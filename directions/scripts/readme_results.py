"""Fill README.md's RESULTS and LIMITS blocks from web/public/data (numbers are never typed by hand)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "web" / "public" / "data"


def load(name):
    p = D / name
    return json.loads(p.read_text()) if p.exists() else None


def other_topics() -> list[str]:
    """One paragraph per other explored topic, read from its own export."""
    topics = (load("topics.json") or {}).get("topics", [])
    out = []
    for t in topics:
        if t.get("default") or t.get("status") != "ready":
            continue
        d = D / t["data"]
        ix = json.loads((d / "index.json").read_text())
        br = json.loads((d / "briefs.json").read_text())
        res = json.loads((d / "results.json").read_text()) if (d / "results.json").exists() else {}
        k = t["counts"]
        surv = sum(r["outcomes"].get("revision_required", 0) + r["outcomes"].get("standing", 0) for r in ix["runs"])
        line = (f"**Second topic: {t['name']}** ({len(t.get('families') or [])} model families: "
                f"{', '.join(t.get('families') or [])}). {k['papers']} papers, {k['objections']} objections, "
                f"{k['trials']} trials ({surv} standing or forcing a revision), {k['briefs']} research directions.")
        if br:
            b = br[0]
            q = (b.get("revision") or {}).get("research_question") or b["research_question"]
            line += f" Strongest lead (lead score {b['score']:.3f}): *{q}*"
        e1 = res.get("e1") or {}
        if e1.get("methods"):
            best = max(e1["methods"], key=lambda m: m.get("recall_at_5", 0))
            kw = next((m for m in e1["methods"] if m["name"].startswith("BM25")), {})
            line += (f" E1 replicated: {best['recall_at_5']:.0%} ({best['name']}) vs {kw.get('recall_at_5', 0):.0%} "
                     f"keyword search (n={e1['n']}).")
        out += ["", line + " Switch topics on the site's /topics page."]
    return out


def outcome_limit(idx: dict) -> str:
    """State which outcomes the gauntlet never produced (computed from the runs)."""
    tot: dict[str, int] = {}
    for r in idx["runs"]:
        for k, v in r["outcomes"].items():
            tot[k] = tot.get(k, 0) + v
    never = [o for o in ("rebutted", "standing", "known_answer") if not tot.get(o)]
    dist = ", ".join(f"{k} {v}" for k, v in sorted(tot.items(), key=lambda kv: -kv[1]))
    s = f"- **The gauntlet's outcome distribution is skewed** ({dist})."
    if never:
        s += (f" No trial ended {' or '.join(never)}: defenders usually save the argument by narrowing a premise, "
              "which the Referee scores as revision_required. Read revision_required as 'the premise needs work', "
              "not as a defeated argument.")
    return s


def block(tag: str, body: str, text: str) -> str:
    start, end = f"<!-- {tag} -->", f"<!-- /{tag} -->"
    new = f"{start}\n{body.strip()}\n{end}"
    if end in text:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), new, text, flags=re.S)
    return text.replace(start, new)


def main() -> None:
    idx, briefs, res, about = load("index.json"), load("briefs.json") or [], load("results.json") or {}, load("about.json") or {}
    if not idx:
        raise SystemExit("run `make export` first")
    c = about.get("corpus", {})
    out = ["## What the lab produced (generated from `web/public/data`)", "",
           f"- Corpus: **{c.get('records')}** OpenAlex records (**{c.get('distinct_works')}** distinct works once "
           f"duplicate versions are merged; {c.get('fresh')} records published since 2026-08-01), "
           f"**{c.get('full_texts')}** open-access full texts.",
           f"- Targets: **{len(idx['targets'])}** papers; **{idx['objections']}** objections generated; "
           f"**{idx['trials']}** full trials; **{idx['briefs']}** research briefs.",
           f"- Model families: {about.get('diversity')} ({', '.join(about.get('families', []))}).", "",
           "| Target | Objections | Trials | Outcomes | Briefs |", "| --- | --- | --- | --- | --- |"]
    for r in idx["runs"]:
        oc = ", ".join(f"{k} {v}" for k, v in sorted(r["outcomes"].items()))
        out.append(f"| {r['title'][:70]} ({r['kind']}) | {r['objections']} | {r['trials']} | {oc} | {len(r['briefs'])} |")
    graded = [b for b in briefs if b.get("assessment")]
    if graded:
        tally = {}
        for b in graded:
            tally[b["assessment"]["grade"]] = tally.get(b["assessment"]["grade"], 0) + 1
        out += ["", f"**Academic quality check** (Assessor agent, a journal-referee read of each direction; grade "
                f"computed from coherence, robustness, significance and specificity): "
                + ", ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
                + f" of {len(graded)}. Each brief shows the strongest objection to it and what the paper would need."]
        revised = [b for b in graded if (b.get("revision") or {}).get("assessment")]
        if revised:
            after: dict[str, int] = {}
            for b in revised:
                g = b["revision"]["assessment"]["grade"]
                after[g] = after.get(g, 0) + 1
            up = sum(1 for b in revised if b["revision"]["assessment"]["overall"] > b["assessment"]["overall"])
            down = sum(1 for b in revised if b["revision"]["assessment"]["overall"] < b["assessment"]["overall"])
            out += ["", f"**Revision round** (each direction rewritten to answer its strongest objection, then re-graded "
                    f"in a fresh read): " + ", ".join(f"{k} {v}" for k, v in sorted(after.items(), key=lambda kv: -kv[1]))
                    + f" of {len(revised)} after revision; overall score up for {up}, down for {down}."]
    if briefs:
        out += ["", "**Top research directions** (lead score = survival × novelty × Assessor quality/5, best first):", ""]
        for b in briefs[:5]:
            q = (b.get("revision") or {}).get("assessment") or b.get("assessment") or {}
            out.append(f"- *{b['research_question']}* — {b['outcome']}, novelty {b['novelty']:.2f}, "
                       f"{b['records_searched']} records searched"
                       + (f"; assessor: {q['grade']} ({q['overall']}/5)" if q else "")
                       + (f"; lead score {b['score']:.3f}" if b.get("score") is not None else "")
                       + ". Further human review required.")
    out += other_topics()
    e1, e2, e3 = res.get("e1"), res.get("e2"), res.get("e3")
    out += ["", "### Evaluation (automatic, no human labels)", ""]
    if e1:
        out += [f"**E1 prior-art recall@5** (n={e1['n']}; scored per work, duplicate records merged):", "",
                "| Method | recall@5 | strict, per record |", "| --- | --- | --- |"]
        out += [f"| {m['name']} | {m['recall_at_5']:.0%} ({m['hits']}/{e1['n']}) | "
                f"{m.get('recall_at_5_strict_record', m['recall_at_5']):.0%} |" for m in e1["methods"]]
        out.append("")
    if e2:
        k, m = e2["known_answer"], e2["misreading"]
        out += [f"**E2 gauntlet calibration**: {k['labelled_known_answer']}/{k['n']} published objections labelled "
                f"known_answer, {k['correct_reply_cited']}/{k['n']} with the correct reply cited and verified; a defender "
                f"cited (verified) a gold reply in {k.get('gold_reply_cited_by_a_defender', '?')}/{k['n']} items; "
                f"{m['caught']}/{m['n']} deliberate misreadings labelled misreading.", ""]
    if e3:
        out += ["**E3 diversity ablation**:", "",
                "| Condition | n | distinct premises / argument | mean pairwise distance | passes pre-screen | novelty > 0.5 |",
                "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {x['name']} | {x['n']} | {x['distinct_premises']} | {x['mean_pairwise_distance']} | "
                f"{x.get('share_passing_prescreen', 0):.0%} | "
                f"{'n/a' if x['share_novelty_gt_05'] is None else format(x['share_novelty_gt_05'], '.0%')} |" for x in e3["conditions"]]
        out.append("")
    if not (e1 or e2 or e3):
        out.append("No evaluation results yet.")
    lim = ["## Limits (read before trusting anything)", "",
           "- **Never a novelty claim.** Novelty is `1 − max similarity` to what our retrieval found in "
           f"{about.get('map_stats', {}).get('claims_indexed', '?')} indexed claims, "
           f"{about.get('map_stats', {}).get('abstracts_indexed', '?')} abstracts and a live OpenAlex query. "
           "Books, paywalled papers and anything OpenAlex lacks are invisible to it.",
           "- **PhilArchive was unavailable**: api.philpapers.org asks for an API key and, with one, no longer serves "
           "OAI-PMH; philarchive.org/oai.pl (the channel PhilPapers' terms name) blocks automated clients, and the terms "
           "forbid mass-querying by scripts, so bulk access needs PhilPapers' agreement. Fresh targets come from OpenAlex "
           "instead, and none of the fresh open-access "
           "full texts was about divine hiddenness itself, so fresh targets are philosophy of religion more broadly.",
           f"- **Model diversity is {about.get('diversity')}.** The design wants Defender A, Defender B and the "
           "Referee from three different families; without Databricks/OpenRouter keys only Anthropic (Claude) and "
           "OpenAI (Codex) models were reachable, through subscription CLIs.",
           outcome_limit(idx),
           "- The Referee and defenders are LLMs; outcome labels are dialectical judgements by models, not verdicts on "
           "truth, and they are noisy. The evals are small (n reported with each) and have no human labels.",
           "- Grounding is audited mechanically: [`docs/AUDIT.md`](docs/AUDIT.md) re-checks every quote, cited id, "
           "deciding sentence and brief reference against its source.",
           "- Reconstructions are the Extractor's; every premise has a verbatim quote, but an author might reconstruct "
           "their argument differently. Read the paper.", ""]
    for name, e in (("E1", e1), ("E2", e2), ("E3", e3)):
        if e and e.get("limits"):
            lim.append(f"- {name}: {e['limits']}")
    text = (ROOT / "README.md").read_text()
    text = block("RESULTS", "\n".join(out), text)
    text = block("LIMITS", "\n".join(lim), text)
    (ROOT / "README.md").write_text(text)
    print("README results/limits updated")


if __name__ == "__main__":
    main()
