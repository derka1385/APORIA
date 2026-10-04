from crux_lab.export import rank_directions


def b(id_, run, survival, novelty, overall=None, revised=None):
    out = {"id": id_, "run_id": run, "survival": survival, "novelty": novelty}
    if overall is not None:
        out["assessment"] = {"grade": "needs work", "overall": overall}
    if revised is not None:
        out["revision"] = {"assessment": {"grade": "needs work", "overall": revised}}
    return out


def test_lead_score_is_survival_novelty_quality():
    briefs = [b("sound-but-known", "A", 0.8, 0.32, 2.5, revised=3.5),   # 0.8 * 0.32 * 0.7 = 0.179
              b("new-and-sound", "B", 0.8, 0.88, 3.0),                 # 0.8 * 0.88 * 0.6 = 0.422
              b("new-but-weak", "B", 0.8, 0.92, 2.75),                 # 0.8 * 0.92 * 0.55 = 0.405
              b("rebutted", "C", 0.3, 0.9, 4.0)]                       # 0.3 * 0.9 * 0.8 = 0.216
    out = rank_directions(briefs)
    assert [x["id"] for x in out] == ["new-and-sound", "new-but-weak", "rebutted", "sound-but-known"]
    assert out[0]["score"] == 0.4224 and out[0]["quality"] == 0.6
    assert out[-1]["quality"] == 0.7   # the revised grade counts, not the first one
    assert [x["tier"] for x in out] == [0, 1, 0, 0]


def test_ungraded_counts_as_middling():
    out = rank_directions([b("x", "A", 1.0, 0.5)])
    assert out[0]["quality"] is None and out[0]["score"] == 0.3


def test_empty():
    assert rank_directions([]) == []
