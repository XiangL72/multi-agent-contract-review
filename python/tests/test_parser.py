# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Tests for decoded English text section splitting."""
from src.parsers.document_parser import parse_raw_text_to_sections

def test_article_headings():
    text = "Article 1 Goods\nThe buyer purchases one unit.\n\nArticle 2 Price\nThe price is CNY 1000.\n\nArticle 3 Liability\nThe seller bears breach liability."
    sections = parse_raw_text_to_sections(text)
    assert len(sections) == 3
    assert "Goods" in sections[0]["title"]
    assert sections[1]["content"] == "The price is CNY 1000."

def test_numbered_headings():
    sections = parse_raw_text_to_sections("1. General\nBoth parties agree.\n\n2. Price\nThe price is CNY 500.")
    assert len(sections) == 2

def test_empty_text():
    assert parse_raw_text_to_sections("") == []

def test_no_sections():
    text = "A contract paragraph without a heading."
    assert parse_raw_text_to_sections(text) == [{"title": "Full text", "content": text}]
