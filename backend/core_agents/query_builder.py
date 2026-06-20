"""
Query builder — Track B (LLM jargon/acronyms, pydantic-structured) +
deterministic consolidation into 20–30 boolean query strings.

Track A synonyms (WordNet/domain thesaurus) and Track B jargon are merged into
per-keyword OR-groups, then combined with AND / ANDNOT operators to maximize
recall while staying inside academic-API query limits.
"""

from __future__ import annotations

import itertools
import json
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from backend.core_agents.llm_provider import chat_completion
except Exception:  # pragma: no cover
    chat_completion = None  # type: ignore[assignment]


class ExpansionResult(BaseModel):
    """Structured Track-B output (validated from the LLM JSON response)."""
    jargon: List[str] = Field(default_factory=list)
    acronyms: List[str] = Field(default_factory=list)
    boolean_clauses: List[str] = Field(default_factory=list)


_TRACK_B_PROMPT = """You are a scientific search-query strategist for the topic: "{topic}".
Core keywords: {keywords}

Identify modern technical jargon, sub-field acronyms, and reusable boolean fragments.
Return ONLY a JSON object with this exact schema (no markdown, no prose):
{{"jargon": ["modern technical term", ...],
  "acronyms": ["ACR = expanded form", ...],
  "boolean_clauses": ["(\\"term a\\" OR \\"term b\\")", ...]}}"""


def _safe_json(text: Optional[str]):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", t)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def llm_expand(topic: str, keywords: List[str]) -> ExpansionResult:
    """Track B: ask a fast LLM for jargon/acronyms/boolean clauses (pydantic)."""
    if chat_completion is None or not keywords:
        return ExpansionResult()
    try:
        raw = chat_completion(
            _TRACK_B_PROMPT.format(topic=topic, keywords=", ".join(keywords[:10])),
            system="You output ONLY valid JSON.",
            max_tokens=500,
            temperature=0.3,
        )
        data = _safe_json(raw)
        if isinstance(data, dict):
            return ExpansionResult(
                jargon=[str(x) for x in data.get("jargon", []) if x][:8],
                acronyms=[str(x) for x in data.get("acronyms", []) if x][:8],
                boolean_clauses=[str(x) for x in data.get("boolean_clauses", []) if x][:8],
            )
    except Exception:  # noqa: BLE001
        pass
    return ExpansionResult()


def _quote(term: str) -> str:
    term = term.strip().strip('"')
    return f'"{term}"' if " " in term else term


def _or_group(term: str, synonyms: List[str], cap: int = 3) -> str:
    alts = [term] + [s for s in (synonyms or []) if s][:cap]
    parts = list(dict.fromkeys(_quote(a) for a in alts))  # dedupe, keep order
    return parts[0] if len(parts) == 1 else "(" + " OR ".join(parts) + ")"


def build_boolean_queries(
    keywords: List[str],
    track_a: Optional[Dict[str, List[str]]] = None,
    track_b: Optional[ExpansionResult] = None,
    target: int = 28,
    exclusions: Optional[List[str]] = None,
) -> List[str]:
    """Generate up to ``target`` deduped boolean query strings (AND/OR/ANDNOT)."""
    track_a = track_a or {}
    track_b = track_b or ExpansionResult()
    keywords = [k for k in (keywords or []) if k and k.strip()][:8]
    if not keywords:
        return []

    groups = {kw: _or_group(kw, track_a.get(kw, [])) for kw in keywords}
    queries: List[str] = []

    # 1. single OR-group per keyword
    queries.extend(groups[kw] for kw in keywords)
    # 2. pairwise AND
    for a, b in itertools.combinations(keywords, 2):
        queries.append(f"{groups[a]} AND {groups[b]}")
    # 3. jargon-augmented (anchor on the top keyword)
    for j in (track_b.jargon or [])[:5]:
        queries.append(f"{groups[keywords[0]]} AND {_quote(j)}")
    # 4. triple AND across the top keywords
    for a, b, c in itertools.combinations(keywords[:5], 3):
        queries.append(f"{groups[a]} AND {groups[b]} AND {groups[c]}")
    # 5. raw Track-B boolean clauses
    queries.extend(c.strip() for c in (track_b.boolean_clauses or [])[:5] if c.strip())
    # 6. exclusion (ANDNOT)
    for e in (exclusions or [])[:2]:
        queries.append(f"{groups[keywords[0]]} ANDNOT {_quote(e)}")

    # Dedupe (case-insensitive), cap.
    seen = set()
    uniq: List[str] = []
    for q in queries:
        qn = q.strip()
        if qn and qn.lower() not in seen:
            seen.add(qn.lower())
            uniq.append(qn)
    return uniq[:target]


def strip_boolean(query: str) -> str:
    """Reduce a boolean query to a plain keyword string for keyword-only APIs
    (Semantic Scholar / CrossRef don't parse AND/OR/NOT)."""
    q = re.sub(r"\b(ANDNOT|AND|OR|NOT)\b", " ", query)
    q = q.replace("(", " ").replace(")", " ").replace('"', " ")
    return re.sub(r"\s{2,}", " ", q).strip()
