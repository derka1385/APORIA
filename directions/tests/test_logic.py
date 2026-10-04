import pytest

from crux_lab.graph.logic import (ParseError, check_skeleton, counterexample, is_valid,
                                  missing_premise_fixes, parse)


def test_modus_ponens_valid():
    assert is_valid(["A -> B", "A"], "B")


def test_affirming_the_consequent_invalid():
    assert not is_valid(["A -> B", "B"], "A")
    assert counterexample(["A -> B", "B"], "A") == {"A": False, "B": True}


def test_added_premise_fixes_invalid_form():
    sk = "A -> B; C |- B"
    assert not check_skeleton(sk)
    assert missing_premise_fixes(sk, "C -> A")
    assert not missing_premise_fixes(sk, "B -> C")


def test_contradictory_missing_premise_rejected():
    assert not missing_premise_fixes("A |- B", "~A")   # makes premises inconsistent


def test_hiddenness_shape():
    # A: perfectly loving God exists; B: God always open to relationship;
    # C: nonresistant nonbelief never occurs; D: nonresistant nonbelief occurs
    sk = "A -> B; B -> C; D; D -> ~C |- ~A"
    assert check_skeleton(sk)


def test_precedence_and_unicode():
    assert str(parse("~A & B -> C | D")) == "((~A & B) -> (C | D))"
    assert is_valid(["A ∧ B"], "A")
    assert is_valid(["A <-> B", "B"], "A")


@pytest.mark.parametrize("bad", ["", "A ->", "I", "(A & B", "A B"])
def test_parse_errors(bad):
    with pytest.raises(ParseError):
        parse(bad)
