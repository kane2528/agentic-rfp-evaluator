"""Lightweight, criterion-aware evidence retrieval with Python's standard library."""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "into", "is", "it", "of", "on", "or", "that", "the", "their", "this",
    "to", "with", "will", "your",
}


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.casefold())
            if len(token) > 1 and token not in _STOP_WORDS]


def _make_chunks(text: str, chunk_chars: int = 1000) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for sentence in sentences:
        # Split unusually long lines so one passage cannot dominate the prompt.
        pieces = [sentence[i:i + chunk_chars] for i in range(0, len(sentence), chunk_chars)]
        for piece in pieces:
            if current and current_size + len(piece) + 1 > chunk_chars:
                chunks.append(" ".join(current))
                current, current_size = [], 0
            current.append(piece)
            current_size += len(piece) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def retrieve_criterion_evidence(
    document_text: str,
    criteria: list[dict[str, Any]],
    top_k: int = 3,
) -> tuple[str, list[dict[str, Any]]]:
    """Build a compact prompt context and an auditable BM25-style retrieval trace."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")
    chunks = _make_chunks(document_text)
    if not chunks:
        raise ValueError("No proposal text was available for evidence retrieval.")
    tokenized = [_tokens(chunk) for chunk in chunks]
    frequencies = [Counter(tokens) for tokens in tokenized]
    document_frequencies = Counter(token for tokens in tokenized for token in set(tokens))
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / max(1, len(lengths))
    audits: list[dict[str, Any]] = []
    sections: list[str] = []

    for criterion in criteria:
        query_tokens = set(_tokens(f"{criterion['name']} {criterion['description']}"))
        scored: list[tuple[float, int]] = []
        for index, counts in enumerate(frequencies):
            score = 0.0
            for token in query_tokens:
                term_frequency = counts[token]
                if not term_frequency:
                    continue
                document_frequency = document_frequencies[token]
                inverse_frequency = math.log(1 + (len(chunks) - document_frequency + 0.5) / (document_frequency + 0.5))
                denominator = term_frequency + 1.2 * (0.25 + 0.75 * lengths[index] / max(1.0, average_length))
                score += inverse_frequency * term_frequency * 2.2 / denominator
            scored.append((score, index))
        # Stable index tie-break keeps output reproducible when terms do not match.
        selected = sorted(scored, key=lambda item: (-item[0], item[1]))[:min(top_k, len(chunks))]
        retrieved = [{"rank": rank, "chunk_id": index + 1, "relevance_score": round(score, 4),
                      "text": chunks[index]}
                     for rank, (score, index) in enumerate(selected, start=1)]
        audits.append({"criterion_id": int(criterion["criterion_id"]), "criterion_name": criterion["name"],
                       "document_chunk_count": len(chunks), "retrieved": retrieved})
        sections.append("\n\n".join(
            f"[Criterion: {criterion['name']} | evidence excerpt {item['rank']} | chunk {item['chunk_id']}]\n{item['text']}"
            for item in retrieved
        ))
    return "\n\n".join(sections), audits
