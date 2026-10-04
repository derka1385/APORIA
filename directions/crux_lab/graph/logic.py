"""Propositional skeletons: parser (atoms A-H, ~ & | -> <->, parentheses) and truth-table validity.

A skeleton is written as premises separated by ';' and the conclusion after '|-' or '∴':
    "A -> B; A |- B"
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

ATOMS = "ABCDEFGH"
_TOKEN = re.compile(r"\s*(<->|->|~|&|\||\(|\)|[A-H])")


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class Node:
    op: str                     # "atom", "~", "&", "|", "->", "<->"
    args: tuple = ()
    name: str = ""

    def eval(self, v: dict[str, bool]) -> bool:
        o = self.op
        if o == "atom":
            return v[self.name]
        a = [x.eval(v) for x in self.args]
        if o == "~":
            return not a[0]
        if o == "&":
            return a[0] and a[1]
        if o == "|":
            return a[0] or a[1]
        if o == "->":
            return (not a[0]) or a[1]
        return a[0] == a[1]

    def atoms(self) -> set[str]:
        return {self.name} if self.op == "atom" else set().union(*(x.atoms() for x in self.args))

    def __str__(self) -> str:
        if self.op == "atom":
            return self.name
        if self.op == "~":
            return f"~{self.args[0]}"
        return f"({self.args[0]} {self.op} {self.args[1]})"


def tokenize(s: str) -> list[str]:
    s = s.replace("¬", "~").replace("∧", "&").replace("∨", "|").replace("→", "->").replace("↔", "<->")
    toks, pos = [], 0
    s = s.rstrip()
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ParseError(f"unexpected character at {pos}: {s[pos:pos + 10]!r}")
        toks.append(m.group(1))
        pos = m.end()
    return toks


def parse(s: str) -> Node:
    toks = tokenize(s)
    if not toks:
        raise ParseError("empty formula")
    i = 0

    def peek():
        return toks[i] if i < len(toks) else None

    def eat(t=None):
        nonlocal i
        tok = peek()
        if tok is None or (t and tok != t):
            raise ParseError(f"expected {t or 'token'}, got {tok}")
        i += 1
        return tok

    def iff():
        left = imp()
        while peek() == "<->":
            eat()
            left = Node("<->", (left, imp()))
        return left

    def imp():
        left = disj()
        if peek() == "->":
            eat()
            return Node("->", (left, imp()))     # right-associative
        return left

    def disj():
        left = conj()
        while peek() == "|":
            eat()
            left = Node("|", (left, conj()))
        return left

    def conj():
        left = unary()
        while peek() == "&":
            eat()
            left = Node("&", (left, unary()))
        return left

    def unary():
        if peek() == "~":
            eat()
            return Node("~", (unary(),))
        if peek() == "(":
            eat("(")
            n = iff()
            eat(")")
            return n
        tok = eat()
        if tok in ATOMS and len(tok) == 1:
            return Node("atom", name=tok)
        raise ParseError(f"unexpected token {tok}")

    node = iff()
    if i != len(toks):
        raise ParseError(f"trailing tokens: {toks[i:]}")
    return node


def split_skeleton(skeleton: str) -> tuple[list[str], str]:
    s = skeleton.replace("∴", "|-").replace("⊢", "|-")
    if "|-" not in s:
        raise ParseError("skeleton needs '|-' before the conclusion")
    prem, concl = s.rsplit("|-", 1)
    premises = [p.strip() for p in re.split(r"[;,]", prem) if p.strip()]
    return premises, concl.strip()


def is_valid(premises: list[str], conclusion: str) -> bool:
    """True iff every valuation making all premises true makes the conclusion true."""
    ps = [parse(p) for p in premises]
    c = parse(conclusion)
    atoms = sorted(set().union(c.atoms(), *(p.atoms() for p in ps)))
    for vals in itertools.product([True, False], repeat=len(atoms)):
        v = dict(zip(atoms, vals))
        if all(p.eval(v) for p in ps) and not c.eval(v):
            return False
    return True


def counterexample(premises: list[str], conclusion: str) -> dict[str, bool] | None:
    ps = [parse(p) for p in premises]
    c = parse(conclusion)
    atoms = sorted(set().union(c.atoms(), *(p.atoms() for p in ps)))
    for vals in itertools.product([True, False], repeat=len(atoms)):
        v = dict(zip(atoms, vals))
        if all(p.eval(v) for p in ps) and not c.eval(v):
            return v
    return None


def satisfiable(formulas: list[str]) -> bool:
    ps = [parse(p) for p in formulas]
    atoms = sorted(set().union(*(p.atoms() for p in ps))) if ps else []
    return any(all(p.eval(dict(zip(atoms, vals))) for p in ps)
               for vals in itertools.product([True, False], repeat=len(atoms)))


def check_skeleton(skeleton: str) -> bool:
    premises, conclusion = split_skeleton(skeleton)
    return is_valid(premises, conclusion)


def missing_premise_fixes(skeleton: str, candidate: str) -> bool:
    """A proposed missing premise must make the argument valid without making premises inconsistent."""
    premises, conclusion = split_skeleton(skeleton)
    parse(candidate)
    return satisfiable(premises + [candidate]) and is_valid(premises + [candidate], conclusion)
