from crux_lab.corpus.dedup import work_ids, work_key


def test_versions_merge_but_shared_titles_by_different_authors_do_not():
    corpus = [
        {"id": "a", "title": "Divine Hiddenness", "authors": ["Jane Doe"]},
        {"id": "b", "title": "Divine  hiddenness.", "authors": ["J. Doe"]},
        {"id": "c", "title": "Divine Hiddenness", "authors": ["Max Roe"]},
    ]
    w = work_ids(corpus)
    assert w == {"a": "a", "b": "a", "c": "c"}
    assert work_key(corpus[0]) == "divine hiddenness|doe"


def test_distinct_nearest_skips_second_copy_of_a_work():
    from crux_lab.corpus.dedup import distinct_nearest
    ms = [{"paper_id": "a", "s": 0.9}, {"paper_id": "a2", "s": 0.8}, {"paper_id": "b", "s": 0.7}, {"paper_id": "c", "s": 0.6}]
    same = {"a": "W1", "a2": "W1", "b": "W2", "c": "W3"}
    out = distinct_nearest(ms, key=lambda m: same[m["paper_id"]])
    assert [m["paper_id"] for m in out] == ["a", "b", "c"]
