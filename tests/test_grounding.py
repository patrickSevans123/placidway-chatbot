"""Unit tests for the deterministic guards.

These are the checks that stop an invented price from reaching a visitor, so
they are tested directly rather than only through the full pipeline.
"""

from __future__ import annotations

from app import guard


EVIDENCE = """
[1] Alternative Adenocarcinoma Cancer Treatment Package in Tijuana, Mexico by ITC
The outpatient program starts at $18,995 USD for three weeks.
The inpatient program is listed at $30,000 USD.
"""


def test_accepts_a_grounded_answer():
    answer = "The outpatient program starts at $18,995 USD for three weeks [1]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert result.ok, result.issues
    assert result.cited == [1]


def test_rejects_an_invented_price():
    answer = "The package costs $9,500 USD [1]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert not result.ok
    assert 9500.0 in result.unsupported_amounts


def test_rejects_an_answer_with_no_citation():
    answer = "The outpatient program starts at $18,995 USD."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert not result.ok
    assert any("citation" in issue for issue in result.issues)


def test_rejects_a_phantom_citation():
    answer = "The program starts at $18,995 USD [7]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=2)
    assert not result.ok
    assert any("not supplied" in issue for issue in result.issues)


def test_rejects_a_price_inside_a_refusal():
    answer = "I don't have that information, but it costs $18,995 USD [1]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert not result.ok
    assert any("claims the information is missing" in issue for issue in result.issues)


def test_normalises_price_formats():
    # "18995" and "$18,995" must be treated as the same amount.
    answer = "It starts at 18995 USD [1]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert result.ok, result.issues


def test_strips_only_the_unsupported_sentence():
    answer = "The outpatient program starts at $18,995 USD [1]. A deposit of $500 USD is required [1]."
    trimmed = guard.strip_unsupported_sentences(answer, EVIDENCE)
    assert "18,995" in trimmed
    assert "500" not in trimmed


def test_amounts_in_handles_both_notations():
    assert guard.amounts_in("$18,995 and 30,000 USD") == [18995.0, 30000.0]


def test_amounts_in_reads_a_bare_grouped_number():
    # A model paraphrasing a price often drops both the currency sign and the
    # word. Until this was handled, that sentence escaped every check.
    assert guard.amounts_in("the package is 18,995") == [18995.0]


def test_amounts_in_still_ignores_counts_and_years():
    assert guard.amounts_in("3 weeks, 19 FAQs, 2026, page 12") == []


def test_money_spans_removes_the_currency_word_with_the_number():
    spans = guard.money_spans("it is 18,995 USD total")
    assert spans == [(6, 16, 18995.0)]
    text = "it is 18,995 USD total"
    start, end, _ = spans[0]
    assert text[start:end] == "18,995 USD"


def test_rejects_a_bare_invented_price():
    answer = "The package is 9,500 [1]."
    result = guard.check(answer, evidence=EVIDENCE, source_count=1)
    assert not result.ok
    assert 9500.0 in result.unsupported_amounts


BLOCKS = {
    1: "[1] Package page\nThe outpatient program starts at $18,995 USD for three weeks.",
    2: "[2] Price list\nAn initial holistic consultation is $50 USD.",
}


def test_rejects_a_price_cited_to_the_wrong_page():
    # The number is real, but the page it points at does not contain it.
    answer = "The package costs $18,995 USD [2]."
    result = guard.check(
        answer, evidence="\n".join(BLOCKS.values()), source_count=2, blocks=BLOCKS
    )
    assert not result.ok
    assert any("does not contain the price" in issue for issue in result.issues)


def test_accepts_a_price_cited_to_the_right_page():
    answer = "The package costs $18,995 USD [1]."
    result = guard.check(
        answer, evidence="\n".join(BLOCKS.values()), source_count=2, blocks=BLOCKS
    )
    assert result.ok, result.issues


def test_accepts_two_prices_cited_to_two_pages():
    answer = "The package is $18,995 USD [1] and a consultation is $50 USD [2]."
    result = guard.check(
        answer, evidence="\n".join(BLOCKS.values()), source_count=2, blocks=BLOCKS
    )
    assert result.ok, result.issues
