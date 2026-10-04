# Adapted from Crux (Univer's earlier project): backend/debate.py. Changes: asymmetric defender/attacker exchange (reply -> rejoinder -> close) instead of symmetric sides, structured concession detection replaces the convergence judge, turn events kept for SSE/replay.
"""The exchange engine. One exchange = Defender reply -> attacker rejoinder (no literature) ->
Defender close. Like Crux, turns run sequentially and every speaker sees the transcript so far;
unlike Crux, the exchange stops early when the defender concedes (detected from a structured
field, not by a judge)."""
from __future__ import annotations

import re
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from crux_lab.agents.roles import render
from crux_lab.graph.schema import Turn
from crux_lab.llm.client import LLMClient, ModelSpec

EventFn = Callable[[dict], Awaitable[None]] | None
_CITE = re.compile(r"\[([A-Za-z0-9_.\-]+\.(?:c|a)\d{1,3})\]")


class DefenderOut(BaseModel):
    misreading_check: str = Field(description="one sentence: does the objection misread the argument?")
    reply: str = Field(description="your reply, at most 250 words, citing literature ids in [brackets]")
    cited_claim_ids: list[str] = Field(default_factory=list)
    concedes: bool = Field(description="true if the argument as stated does not survive this objection")
    revised_premise: str | None = Field(default=None, description="the new or changed premise needed, one sentence, or null")


def render_transcript(turns: list[Turn]) -> str:
    """Render prior turns into the text a speaker sees (same shape as Crux's _render_transcript)."""
    names = {"defender_a": "Defender A", "defender_b": "Defender B", "attacker": "Objector"}
    blocks = [f"### {names.get(t.speaker, t.speaker)} — {t.phase}\n{t.content}" for t in turns]
    return "\n\n".join(blocks) if blocks else "(nothing yet)"


def cited_ids(text: str, declared: list[str]) -> list[str]:
    return list(dict.fromkeys(declared + _CITE.findall(text)))


INSTRUCTIONS = {
    "reply": ("Reply to the objection. First say whether it misreads the argument, then answer it. "
              "If the argument survives only with a new or changed premise, concede and state it."),
    "close": ("Close the exchange: answer the objector's rejoinder and give your final position. "
              "If the argument as stated does not survive, concede and state the premise it would need."),
}
STANCE = {
    "defender_a": "- You are the firmer defender: concede only what you must.",
    "defender_b": ("- You are the more concessive defender: where the objection lands even partly, say so "
                   "and look for the smallest premise change that would save the argument."),
}


async def defender_turn(client: LLMClient, speaker: str, spec: ModelSpec, phase: str, argument: str,
                        objection: str, target_id: str, literature: str, turns: list[Turn],
                        exchange: int) -> Turn:
    system, user = render("defender", defender_name="Defender " + speaker[-1].upper(),
                          stance=STANCE[speaker], argument=argument, objection=objection,
                          target_id=target_id, literature=literature or "(none retrieved)",
                          transcript=render_transcript(turns), instruction=INSTRUCTIONS[phase])
    out, c = await client.json(speaker, user, DefenderOut, system, spec=spec, max_tokens=2000)
    if not out:
        return Turn(exchange=exchange, speaker=speaker, phase=phase, model=spec.model, family=spec.family,
                    content="(no valid reply: the model output failed validation three times)")
    content = out.reply.strip()
    if out.concedes and out.revised_premise:
        content += f"\n\nRevised premise: {out.revised_premise.strip()}"
    return Turn(exchange=exchange, speaker=speaker, phase=phase, model=spec.model, family=spec.family,
                content=content, cited_claim_ids=cited_ids(out.reply, out.cited_claim_ids),
                concedes=out.concedes, revised_premise=(out.revised_premise or None))


async def attacker_turn(client: LLMClient, spec: ModelSpec, argument: str, objection: str, target_id: str,
                        turns: list[Turn], exchange: int) -> Turn:
    system, user = render("attacker_rejoinder", argument=argument, objection=objection, target_id=target_id,
                          transcript=render_transcript(turns))
    c = await client.chat("attacker", user, system, spec=spec, max_tokens=800)
    return Turn(exchange=exchange, speaker="attacker", phase="rejoinder", model=spec.model,
                family=spec.family, content=c.text.strip())


async def run_exchange(client: LLMClient, *, speaker: str, defender: ModelSpec, attacker: ModelSpec,
                       argument: str, objection: str, target_id: str, literature: str,
                       exchange: int, on_event: EventFn = None) -> list[Turn]:
    turns: list[Turn] = []

    async def emit(t: Turn):
        turns.append(t)
        if on_event:
            await on_event({"type": "turn", "turn": t.model_dump()})

    await emit(await defender_turn(client, speaker, defender, "reply", argument, objection, target_id,
                                   literature, turns, exchange))
    if turns[-1].concedes:       # stopping rule: a concession ends the exchange
        return turns
    await emit(await attacker_turn(client, attacker, argument, objection, target_id, turns, exchange))
    await emit(await defender_turn(client, speaker, defender, "close", argument, objection, target_id,
                                   literature, turns, exchange))
    return turns
