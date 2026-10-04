from crux_lab.graph.schema import Objection
from crux_lab.lab import director


def obj(i, agent="blind_thought_experimenter", family="a", target="p1", depth=0):
    return Objection(id=f"o{i}", argument_id="arg", target_premise_id=target, kind="k", text="t",
                     agent=agent, model="m", family=family, depth=depth)


def test_priority_formula():
    assert director.priority(0.5, 1.0, 1.0, 1) == 0.5 * 1.0 * 1.0 + 0.1
    assert director.priority(1.0, 0.4, 0.0, 0) == 0.2


def test_rank_orders_by_priority_and_exploration():
    objs = [obj(1, family="a"), obj(2, family="b"), obj(3, family="a", target="p2")]
    nov = {"o1": 0.9, "o2": 0.5, "o3": 0.9}
    C = {"p1": 0.2, "p2": 1.0}
    rows = director.rank(objs, nov, C, tried_keys=set())
    assert [r.objection_id for r in rows] == ["o3", "o1", "o2"]
    # once family a has been tried on this argument, b gets the exploration bonus
    rows = director.rank(objs, nov, C, tried_keys={"blind_thought_experimenter|a"})
    assert rows[0].E == 0 and {r.objection_id: r.E for r in rows}["o2"] == 1


def test_rank_skips_tried_objections_and_reorders():
    objs = [obj(1), obj(2, family="b")]
    rows = director.rank(objs, {"o1": 0.9, "o2": 0.1}, {"p1": 0.5}, set(), outcomes={"o1": "standing"})
    assert [r.objection_id for r in rows] == ["o2"]
