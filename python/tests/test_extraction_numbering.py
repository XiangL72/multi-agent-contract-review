"""Unnumbered clauses may omit metadata without weakening source validation."""
import pytest
from pydantic import ValidationError

from src.agents.clause_extraction import ClauseExtractionAgent
from src.harness.errors import ReviewStageError

TEXT = "The price is not agreed."


def clause(**overrides):
    return {"title": "Price", "content": TEXT, "category": "payment", **overrides}


@pytest.mark.parametrize("metadata,expected", [
    ({}, ""),
    ({"section_number": None}, ""),
    ({"section_number": ""}, ""),
    ({"section_number": "2.1"}, "2.1"),
])
def test_optional_numbering_preserves_source_and_category(metadata, expected):
    result = ClauseExtractionAgent()._parse_clauses({"clauses": [clause(**metadata)]}, TEXT)
    assert result[0].section_number == expected
    assert result[0].category.value == "payment"
    assert TEXT[result[0].start:result[0].end] == result[0].content == TEXT


@pytest.mark.parametrize("invalid", [0, False, 1.5, [], {}])
def test_invalid_numbering_types_are_not_silently_erased(invalid):
    with pytest.raises(ValidationError):
        ClauseExtractionAgent()._parse_clauses(
            {"clauses": [clause(section_number=invalid)]}, TEXT)


def test_multiple_null_numbered_clauses_keep_distinct_spans():
    parts = ["The price is not agreed.", "The seller assumes unlimited liability."]
    text = "\n".join(parts)
    payload = {"clauses": [clause(content=part, section_number=None) for part in parts]}
    result = ClauseExtractionAgent()._parse_clauses(payload, text)
    assert [item.section_number for item in result] == ["", ""]
    assert result[0].end < result[1].start
    assert all(text[item.start:item.end] == item.content for item in result)


@pytest.mark.parametrize("invalid_content", [None, "", "An invented source sentence."])
def test_null_numbering_does_not_hide_invalid_required_content(invalid_content):
    with pytest.raises(ReviewStageError):
        ClauseExtractionAgent()._parse_clauses(
            {"clauses": [clause(content=invalid_content, section_number=None)]}, TEXT)


def test_null_numbering_does_not_hide_invalid_category():
    with pytest.raises(ValueError):
        ClauseExtractionAgent()._parse_clauses(
            {"clauses": [clause(category="invented", section_number=None)]}, TEXT)
