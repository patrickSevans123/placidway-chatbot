"""Tests for the text cleanup that runs before chunking.

The price-list page ships an unrendered PHP placeholder into its article text.
Left in place it becomes a retrievable chunk that tells the model a price range
exists when the page states none.
"""

from __future__ import annotations

from app.extract import _strip_placeholders


def test_removes_a_php_placeholder():
    text = "prices range between =$priceRange?> in Tijuana, Mexico"
    assert "priceRange" not in _strip_placeholders(text)
    assert "Tijuana" in _strip_placeholders(text)


def test_removes_a_brace_placeholder():
    assert "{{" not in _strip_placeholders("Cost is {{ price }} USD")


def test_removes_a_php_block():
    assert "echo" not in _strip_placeholders("Hello <?php echo $x; ?> world")


def test_keeps_a_real_price():
    text = "The outpatient program starts at $18,995 USD for three weeks."
    assert _strip_placeholders(text) == text


def test_keeps_ordinary_punctuation():
    text = "Is the price = the same? Yes."
    assert _strip_placeholders(text) == text
