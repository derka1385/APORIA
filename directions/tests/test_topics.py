import os
import subprocess
import sys

from crux_lab import config


def test_default_topic_keeps_original_paths():
    assert config.DEFAULT_TOPIC == "divine-hiddenness"
    p = config.topic_paths("divine-hiddenness")
    assert p["corpus"] == config.ROOT / "data" / "corpus.jsonl"
    assert p["web"] == config.ROOT / "web" / "public" / "data"
    assert p["results"] == config.ROOT / "results"


def test_other_topic_gets_its_own_dirs():
    p = config.topic_paths("fine-tuning")
    assert p["corpus"] == config.ROOT / "data" / "topics" / "fine-tuning" / "corpus.jsonl"
    assert p["web"] == config.ROOT / "web" / "public" / "data" / "topics" / "fine-tuning"
    assert p["index"] == config.ROOT / "cache" / "index" / "fine-tuning"


def test_every_topic_config_is_complete():
    for slug, t in config.TOPICS.items():
        for key in ("slug", "name", "description", "area", "queries", "fresh_queries", "relevant",
                    "relevance_levels", "schools"):
            assert t.get(key), (slug, key)
        assert len(t["relevance_levels"]) == 4 and len(t["schools"]) >= 2


def test_hiddenness_queries_unchanged():
    from crux_lab.corpus import openalex
    assert openalex.QUERIES == ["divine hiddenness", "nonresistant nonbelief", "divine silence", "hiddenness of God",
                                "skeptical theism hiddenness", "Schellenberg hiddenness argument"]
    assert openalex.SEARCH_STRINGS["divine hiddenness"] == '"divine hiddenness"'


def test_topic_env_switches_queries_and_schools():
    code = ("from crux_lab.corpus import openalex; from crux_lab.lab import generators; "
            "print(openalex.QUERIES[0]); print(generators.SCHOOLS[0])")
    env = {**os.environ, "CRUX_LAB_TOPIC": "fine-tuning"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout
    assert out.splitlines() == ["fine-tuning argument", "Bayesian confirmation theory"]


def test_spread_takes_one_target_per_search_in_topic_order(monkeypatch):
    from crux_lab.corpus import targets as tg
    monkeypatch.setattr(tg, "TOPIC", {"queries": {"newcomb": "", "wager": "", "worlds": ""}})
    mk = lambda rel: tg.Screen(in_area=True, argues_for_thesis=True, english=True, topic_relevance=rel,  # noqa: E731
                               argument_clarity=2)
    ranked = [{"id": "w1", "query": "wager"}, {"id": "w2", "query": "wager"}, {"id": "n1", "query": "newcomb"},
              {"id": "x", "query": "worlds"}, {"id": "w3", "query": "wager"}]
    screens = {"w1": mk(3), "w2": mk(3), "n1": mk(1), "x": mk(0), "w3": mk(3)}
    out = [p["id"] for p in tg.spread(ranked, screens, min_score=4)]
    assert out == ["n1", "w1", "w2", "w3"]   # newcomb first (topic order); "x" scores 2 < 4 and is left out


def test_fulltext_quota_keeps_room_for_classics(monkeypatch):
    from crux_lab.corpus import build
    monkeypatch.setattr(build.pdf, "get_fulltext", lambda pid, url: "text")
    monkeypatch.setattr(build.pdf, "text_path", lambda pid: build.RAW / f"{pid}.txt")
    papers = [{"id": f"f{i}", "pdf_url": "u", "fresh": True} for i in range(10)] + \
             [{"id": f"c{i}", "pdf_url": "u", "cited_by_count": i} for i in range(10)]
    assert build.fulltexts(papers, limit=4, fresh_share=0.5) == 4
    # half the quota for fresh papers, the rest for the most-cited classics
    assert sorted(p["id"] for p in papers if p.get("pdf_path")) == ["c8", "c9", "f0", "f1"]


def test_recent_paper_found_by_a_classic_search_counts_as_fresh(monkeypatch):
    from crux_lab.corpus import build
    monkeypatch.setattr(build, "FRESH_FROM", "2026-08-01")
    papers = [{"id": "new", "publication_date": "2026-09-10"}, {"id": "old", "publication_date": "2022-05-06"},
              {"id": "flagged", "fresh": True, "publication_date": "2026-08-03"}, {"id": "undated"}]
    assert build.mark_recent(papers) == 1
    assert [p["id"] for p in papers if p.get("fresh")] == ["new", "flagged"]
