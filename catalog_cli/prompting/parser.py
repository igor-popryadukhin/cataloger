from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class ParsedResponse:
    raw_lines: List[str]
    normalized_paths: List[str]


_CLEAN_PREFIXES = ("- ", "* ", "• ", "1. ", "2. ")


def _strip_markers(line: str) -> str:
    line = line.strip().strip("`")
    for prefix in _CLEAN_PREFIXES:
        if line.startswith(prefix):
            line = line[len(prefix) :]
    return line.strip()


def _normalize_slashes(line: str) -> str:
    line = re.sub(r"\\+", "/", line)
    line = re.sub(r"/+", "/", line)
    return line.strip("/")


def parse_response(sphere: str, response_text: str) -> ParsedResponse:
    raw_lines = [line for line in response_text.splitlines() if line.strip()]
    cleaned: List[str] = []
    for line in raw_lines:
        normalized = _strip_markers(line)
        if not normalized:
            continue
        normalized = _normalize_slashes(normalized)
        normalized = re.sub(r"\s+/\s+", "/", normalized)
        normalized = re.sub(r"\s{2,}", " ", normalized)
        cleaned.append(normalized)

    deduped: List[str] = []
    seen = set()
    sphere_lower = sphere.lower().strip()
    for line in cleaned:
        candidate = line
        if not candidate:
            continue
        if not candidate.lower().startswith(sphere_lower + "/"):
            if candidate.lower().startswith(sphere_lower):
                candidate = f"{sphere}{candidate[len(sphere):]}"
            else:
                candidate = f"{sphere}/{candidate}"
        segments = [segment.strip() for segment in candidate.split("/") if segment.strip()]
        if len(segments) < 3:
            continue
        normalized_path = "/".join(segments)
        key = normalized_path.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized_path)

    return ParsedResponse(raw_lines=raw_lines, normalized_paths=deduped)
