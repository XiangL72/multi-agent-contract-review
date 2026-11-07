# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Split decoded text at English numbered or Markdown headings."""
from __future__ import annotations
import re

def parse_raw_text_to_sections(text: str) -> list[dict]:
    sections = []
    last_pos, last_title = 0, "Preamble"
    pattern = r"^(?:\d+[.)]\s+.+|(?:Article|Section)\s+\d+[.:]?\s*.*|\#{1,6}\s+.+)$"
    for match in re.finditer(pattern, text, re.M | re.I):
        content = text[last_pos:match.start()].strip()
        if content:
            sections.append({"title": last_title, "content": content})
        last_title, last_pos = match.group(0).strip(), match.end()
    remaining = text[last_pos:].strip()
    if remaining:
        sections.append({"title": last_title if last_pos else "Full text", "content": remaining})
    return sections
