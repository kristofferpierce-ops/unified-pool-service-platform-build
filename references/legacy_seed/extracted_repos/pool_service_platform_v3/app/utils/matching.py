from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Tuple


def normalize_text(value: str) -> str:
    value = value or ""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9.%/ -]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def best_match(query: str, candidates: Iterable[Tuple[int, str]]) -> tuple[int | None, float, list[tuple[int, str, float]]]:
    scored = []
    for candidate_id, label in candidates:
        score = similarity(query, label)
        scored.append((candidate_id, label, score))
    scored.sort(key=lambda x: x[2], reverse=True)
    top = scored[:5]
    if not top:
        return None, 0.0, []
    return top[0][0], top[0][2], top
