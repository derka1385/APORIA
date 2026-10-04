"""Tool layer: things the system checks instead of letting the LLM guess.

Every tool is a plain function registered in TOOLS with a one-line purpose.
Reasoners only see the tools their policy allows; the controller decides when a
tool is needed (see engine.Reasoner.op_formalize / op_memory).
"""

from __future__ import annotations

import ast
import itertools
import operator
import re

TOOLS: dict[str, dict] = {}


def tool(name: str, purpose: str):
    def reg(fn):
        TOOLS[name] = {"fn": fn, "purpose": purpose}
        return fn
    return reg


# ------------------------------------------------------------- propositional logic

_TOK = re.compile(r"\s*(<->|->|[()~!&|]|[A-Za-z][A-Za-z0-9_]*)")


def _tokens(s: str) -> list[str]:
    s = s.replace("∧", "&").replace("∨", "|").replace("¬", "~").replace("→", "->").replace("↔", "<->")
    out, pos = [], 0
    while pos < len(s.rstrip()):
        m = _TOK.match(s, pos)
        if not m:
            raise ValueError(f"cannot parse {s[pos:pos + 12]!r}")
        t = m.group(1)
        out.append({"and": "&", "or": "|", "not": "~", "implies": "->", "iff": "<->"}.get(t.lower(), t)
                   if t.lower() in ("and", "or", "not", "implies", "iff") else t)
        pos = m.end()
    return out


def parse(s: str):
    """Recursive descent: iff < implies (right assoc) < or < and < not < atom."""
    toks, i = _tokens(s), 0

    def peek():
        return toks[i] if i < len(toks) else None

    def eat(t=None):
        nonlocal i
        if t and peek() != t:
            raise ValueError(f"expected {t} in {s!r}")
        i += 1
        return toks[i - 1]

    def iff():
        a = imp()
        while peek() == "<->":
            eat(); a = ("iff", a, imp())
        return a

    def imp():
        a = disj()
        if peek() == "->":
            eat(); return ("imp", a, imp())
        return a

    def disj():
        a = conj()
        while peek() == "|":
            eat(); a = ("or", a, conj())
        return a

    def conj():
        a = neg()
        while peek() == "&":
            eat(); a = ("and", a, neg())
        return a

    def neg():
        if peek() in ("~", "!"):
            eat(); return ("not", neg())
        if peek() == "(":
            eat("("); a = iff(); eat(")"); return a
        t = eat()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", t or ""):
            raise ValueError(f"unexpected {t!r} in {s!r}")
        return ("atom", t)

    tree = iff()
    if i != len(toks):
        raise ValueError(f"trailing tokens in {s!r}")
    return tree


def _atoms(t, acc):
    if t[0] == "atom":
        acc.add(t[1])
    else:
        for c in t[1:]:
            _atoms(c, acc)
    return acc


def _ev(t, v):
    k = t[0]
    if k == "atom": return v[t[1]]
    if k == "not": return not _ev(t[1], v)
    if k == "and": return _ev(t[1], v) and _ev(t[2], v)
    if k == "or": return _ev(t[1], v) or _ev(t[2], v)
    if k == "imp": return (not _ev(t[1], v)) or _ev(t[2], v)
    return _ev(t[1], v) == _ev(t[2], v)


@tool("logic_check", "truth-table validity of a propositional argument, with a countermodel if invalid")
def logic_check(premises: list[str], conclusion: str) -> dict:
    ps, c = [parse(p) for p in premises], parse(conclusion)
    atoms = sorted(set().union(*(_atoms(t, set()) for t in ps + [c])))
    if len(atoms) > 12:
        raise ValueError("too many atoms for a truth table")
    consistent = False
    for vals in itertools.product([True, False], repeat=len(atoms)):
        v = dict(zip(atoms, vals))
        if all(_ev(p, v) for p in ps):
            consistent = True
            if not _ev(c, v):
                return {"valid": False, "consistent": True, "countermodel": v, "atoms": atoms}
    return {"valid": consistent, "consistent": consistent, "countermodel": None, "atoms": atoms}


@tool("theorem_prover", "first-order proof search (interface only; falls back to the propositional checker)")
def theorem_prover(premises: list[str], conclusion: str) -> dict:
    # ponytail: no FOL prover bundled; plug one in here (e.g. Vampire/Prover9 via subprocess) with the same signature
    return {**logic_check(premises, conclusion), "engine": "propositional-fallback"}


# ------------------------------------------------------------- calculation

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}


@tool("calculator", "safe arithmetic evaluation")
def calculator(expr: str) -> float:
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("unsupported expression")
    return ev(ast.parse(expr, mode="eval"))


# ------------------------------------------------------------- retrieval / similarity / graph
# These wrap engine functions; registered here so every tool call goes through one log.

def register_engine_tools(literature_search, ltm_search, similarity, graph_query):
    tool("literature_search", "nearest (or deliberately distant) entries in the local literature corpus")(literature_search)
    tool("memory_search", "long-term memory of past sessions: hypotheses, objections, assumptions, outcomes")(ltm_search)
    tool("similarity", "embedding cosine similarity between two texts")(similarity)
    tool("graph_query", "structural queries over the argument graph (weakest assumption, dependents, attackers)")(graph_query)


def call(name: str, allowed, *args, **kw):
    """Run a tool the policy allows; returns (ok, result_or_error)."""
    if name not in TOOLS or (allowed is not None and name not in allowed):
        return False, f"tool {name} not available"
    try:
        return True, TOOLS[name]["fn"](*args, **kw)
    except Exception as ex:  # a tool failure is information, not a crash
        return False, str(ex)


if __name__ == "__main__":
    assert logic_check(["P -> Q", "P"], "Q")["valid"]
    r = logic_check(["P -> Q", "Q"], "P")
    assert not r["valid"] and r["countermodel"] == {"P": False, "Q": True}
    assert logic_check(["P", "~P"], "Q") == {"valid": False, "consistent": False, "countermodel": None, "atoms": ["P", "Q"]}
    assert logic_check(["A and B implies C", "A", "B"], "C")["valid"]
    assert logic_check(["(A <-> B)", "~B"], "~A")["valid"]
    assert calculator("2 * (3 + 4) ** 2") == 98
    assert call("calculator", ["logic_check"], "1+1")[0] is False
    print("ok")
