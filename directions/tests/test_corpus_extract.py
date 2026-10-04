from crux_lab.corpus.openalex import rebuild_abstract, to_paper
from crux_lab.corpus.philarchive_oai import parse_records, rec_id, to_paper as oai_paper
from crux_lab.graph.extract import chunk_text, quote_found, sentence_count, strip_references
from crux_lab.graph.formalize import FormalOut, MissingPremise, validator

OAI = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
 xmlns:dc="http://purl.org/dc/elements/1.1/"><ListRecords>
 <record><header><identifier>oai:philarchive.org/rec/ABCD-2</identifier><datestamp>2026-08-03T10:00:00Z</datestamp></header>
 <metadata><oai_dc:dc><dc:title>Hiddenness Again</dc:title><dc:creator>Doe, Jane</dc:creator>
 <dc:subject>Philosophy of Religion</dc:subject><dc:description>I argue that God is not hidden.</dc:description>
 <dc:date>2026</dc:date><dc:identifier>https://philarchive.org/rec/ABCD-2</dc:identifier></oai_dc:dc></metadata></record>
 <record><header status="deleted"><identifier>oai:philarchive.org/rec/GONE</identifier><datestamp>2026-08-04T00:00:00Z</datestamp></header></record>
 <resumptionToken>tok123</resumptionToken></ListRecords></OAI-PMH>"""


def test_oai_parse_and_paper():
    recs, tok = parse_records(OAI)
    assert tok == "tok123" and len(recs) == 2 and recs[1]["deleted"]
    p = oai_paper(recs[0])
    assert p["id"] == "pa:ABCD-2" and p["year"] == 2026 and p["authors"] == ["Doe, Jane"]
    assert p["pdf_url"] == "https://philarchive.org/archive/ABCD-2" and rec_id(recs[0]["oai_id"]) == "ABCD-2"


def test_oai_no_records():
    xml = '<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="noRecordsMatch">none</error></OAI-PMH>'
    assert parse_records(xml) == ([], None)


def test_openalex_abstract_and_paper():
    inv = {"God": [0], "is": [1], "hidden": [2]}
    assert rebuild_abstract(inv) == "God is hidden"
    w = {"id": "https://openalex.org/W1", "display_name": "T", "publication_year": 2020, "abstract_inverted_index": inv,
         "authorships": [{"author": {"display_name": "A B"}}], "best_oa_location": {"pdf_url": "http://x/p.pdf"},
         "primary_location": {"source": {"display_name": "Sophia"}}, "doi": "https://doi.org/10.1/x"}
    p = to_paper(w, "q")
    assert p["id"] == "oa:W1" and p["venue"] == "Sophia" and p["pdf_url"] == "http://x/p.pdf" and p["url"].startswith("https://doi")


def test_quote_verification():
    src = "The argument fails.  God, if perfectly loving, would always be open to a relationship\nwith us. Next."
    assert quote_found("God, if perfectly loving, would always be open to a relationship with us.", src)
    assert quote_found("God if perfectly loving would always be open to a relationship with us", src)
    assert not quote_found("God would never hide from anyone who seeks a relationship.", src)
    assert not quote_found("short", src)
    assert sentence_count("One. Two. Three.") == 3


def test_chunking_drops_references():
    body = ("Paragraph about hiddenness. " * 300 + "\n\n") * 4
    text = body + "\nReferences\nSmith, J. (2001). A book.\n" * 1
    chunks = chunk_text(text, size=4000, overlap=200)
    assert len(chunks) >= 3 and all("Smith, J." not in c for c in chunks)
    assert "References" not in strip_references(text)[-200:]


def test_formalizer_validator():
    check = validator(["p1", "p2"])
    ok = FormalOut(atoms={"A": "a", "B": "b"}, premise_formulas={"p1": "A -> B", "p2": "A"}, conclusion_formula="B")
    assert check(ok) is None
    invalid = FormalOut(atoms={"A": "a", "B": "b", "C": "c"}, premise_formulas={"p1": "A -> B", "p2": "C"},
                        conclusion_formula="B")
    assert "NOT entail" in check(invalid)
    fixed = invalid.model_copy(update={"missing_premise": MissingPremise(text="c gives a", formula="C -> A")})
    assert check(fixed) is None
    bad_fix = invalid.model_copy(update={"missing_premise": MissingPremise(text="x", formula="B -> C")})
    assert "does not make the argument valid" in check(bad_fix)
    assert "undeclared" in check(ok.model_copy(update={"conclusion_formula": "D"}))
    assert "missing" in check(ok.model_copy(update={"premise_formulas": {"p1": "A"}}))
