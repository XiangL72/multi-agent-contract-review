"""Versioned knowledge loading and deterministic, applicability-filtered retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_KNOWLEDGE = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "civil_code.jsonl"


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    title: str
    text: str
    url: str
    jurisdiction: str
    effective_from: date
    effective_to: date | None
    source_version: str
    retrieved_at: date
    review_status: str
    keywords: tuple[str, ...]
    english_gloss: str = ""
    english_gloss_status: str = "unreviewed_translation"

    @classmethod
    def from_dict(cls, value: dict) -> "KnowledgeChunk":
        return cls(
            chunk_id=value["chunk_id"], source=value["source"],
            title=value["title"], text=value["text"],
            url=value["url"], jurisdiction=value["jurisdiction"],
            effective_from=date.fromisoformat(value["effective_from"]),
            effective_to=date.fromisoformat(value["effective_to"]) if value.get("effective_to") else None,
            source_version=value["source_version"], retrieved_at=date.fromisoformat(value["retrieved_at"]),
            review_status=value["review_status"],
            keywords=tuple(value["keywords"]),
            english_gloss=value.get("english_gloss", ""),
            english_gloss_status=value.get("english_gloss_status", "unreviewed_translation"),
        )


@dataclass(frozen=True)
class RetrievalResult:
    chunks: tuple[KnowledgeChunk, ...]
    eligible_count: int
    knowledge_version: str


class KnowledgeStore:
    def __init__(self, chunks: list[KnowledgeChunk]):
        ids = [chunk.chunk_id for chunk in chunks]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate knowledge chunk ID")
        self.chunks = tuple(chunks)

    @classmethod
    def load(cls, path: Path = DEFAULT_KNOWLEDGE) -> "KnowledgeStore":
        chunks = []
        with path.open(encoding="utf-8") as source:
            for number, line in enumerate(source, start=1):
                if line.strip():
                    try:
                        chunks.append(KnowledgeChunk.from_dict(json.loads(line)))
                    except (KeyError, ValueError, TypeError) as exc:
                        raise ValueError(f"Invalid knowledge row {number}") from exc
        return cls(chunks)

    def retrieve(self, query: str, *, jurisdiction: str, as_of: date, top_k: int = 3) -> RetrievalResult:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        eligible = [chunk for chunk in self.chunks if
                    chunk.review_status == "reviewed"
                    and chunk.jurisdiction == jurisdiction
                    and chunk.effective_from <= as_of
                    and (chunk.effective_to is None or as_of < chunk.effective_to)]
        scored = []
        for chunk in eligible:
            score = sum(len(word) for word in chunk.keywords
                        if re.search(r"\b" + re.escape(word.casefold()) + r"\b", query.casefold()))
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        versions = sorted({chunk.source_version for chunk in eligible})
        return RetrievalResult(tuple(chunk for _, chunk in scored[:top_k]), len(eligible), ",".join(versions))


def validate_citation(value: dict, retrieved: RetrievalResult) -> dict:
    """A citation is valid only if its exact quote was in this run's retrieved context."""
    if not isinstance(value, dict):
        raise ValueError("Citation must be an object")
    for chunk in retrieved.chunks:
        if (value.get("chunk_id") == chunk.chunk_id
                and value.get("source_version") == chunk.source_version
                and isinstance(value.get("quote"), str)
                and value["quote"]
                and value["quote"] in chunk.text):
            return {"chunk_id": chunk.chunk_id, "source": chunk.source,
                    "title": chunk.title, "source_version": chunk.source_version,
                    "quote": value["quote"], "url": chunk.url,
                    "jurisdiction": chunk.jurisdiction,
                    "retrieved_at": chunk.retrieved_at.isoformat(),
                    "effective_from": chunk.effective_from.isoformat(),
                    "effective_to": chunk.effective_to.isoformat() if chunk.effective_to else None,
                    "english_gloss": chunk.english_gloss,
                    "english_gloss_status": chunk.english_gloss_status,
                    "text_kind": "source_summary"}
    raise ValueError("Citation is absent from this run's applicable retrieval context")
