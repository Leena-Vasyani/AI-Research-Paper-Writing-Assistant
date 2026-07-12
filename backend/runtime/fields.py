"""
Field (discipline) behavior map — backend counterpart to ``web/src/lib/fields.ts``.

The frontend sends ``{ field, subfield }`` inside the pipeline ``constraints``.
This module turns the broad ``field`` id into:

  * a **retrieval source profile** — which scholarly sources to query and in what
    priority (arXiv is CS/physics-heavy, so non-STEM fields lean on OpenAlex /
    Semantic Scholar / CrossRef which index every discipline), and
  * a **coarse domain** ('cs' | 'health' | 'general') reused for the Search
    Agent's per-source result allocation, and
  * a short **prompt hint** injected into agent prompts so generated content uses
    the discipline's conventions, terminology, and expected structure.

Keep the field ids in sync with the frontend taxonomy. Unknown / missing fields
fall back to "general", which preserves today's auto-classified behavior.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Every scholarly source the Search Agent knows how to fetch.
ALL_SOURCES: List[str] = ["arxiv", "pubmed", "openalex", "semantic_scholar", "crossref"]

# Field id -> ordered preferred sources. First entries get the larger result
# allocation in the Search Agent.
FIELD_SOURCES: Dict[str, List[str]] = {
    "general": ["arxiv", "pubmed", "openalex", "semantic_scholar", "crossref"],
    "cs": ["arxiv", "semantic_scholar", "crossref"],
    "engineering": ["arxiv", "semantic_scholar", "crossref", "openalex"],
    "physical_sciences": ["arxiv", "semantic_scholar", "openalex", "crossref"],
    "health": ["pubmed", "semantic_scholar", "crossref"],
    "life_sciences": ["pubmed", "openalex", "semantic_scholar", "crossref"],
    "agriculture": ["openalex", "semantic_scholar", "crossref", "pubmed"],
    "environment": ["openalex", "semantic_scholar", "crossref", "arxiv"],
    "social_sciences": ["openalex", "semantic_scholar", "crossref"],
    "finance": ["openalex", "semantic_scholar", "crossref", "arxiv"],
    "business": ["openalex", "semantic_scholar", "crossref"],
    "arts": ["openalex", "semantic_scholar", "crossref"],
    "law": ["openalex", "semantic_scholar", "crossref"],
}

# Field id -> coarse domain, reused for the Search Agent's allocation weighting.
_FIELD_DOMAIN: Dict[str, str] = {
    "cs": "cs",
    "engineering": "cs",
    "physical_sciences": "cs",
    "health": "health",
    "life_sciences": "health",
    "agriculture": "health",
    "general": "general",
    "environment": "general",
    "social_sciences": "general",
    "finance": "general",
    "business": "general",
    "arts": "general",
    "law": "general",
}

# Field id -> (human label, one-line convention hint used in prompts).
_FIELD_HINT: Dict[str, str] = {
    "general": (
        "general/interdisciplinary research",
        "clear academic prose with an evidence-based, methodical structure",
    ),
    "cs": (
        "Computer Science",
        "precise technical terminology, algorithms/systems framing, and an "
        "IEEE-style Introduction / Related Work / Method / Experiments structure",
    ),
    "engineering": (
        "Engineering",
        "quantitative, design-and-analysis framing with methods, results, and "
        "validation against requirements",
    ),
    "physical_sciences": (
        "Physical Sciences",
        "formal scientific conventions with hypotheses, methods, quantitative "
        "results, and error analysis",
    ),
    "health": (
        "Health & Medicine",
        "clinical/biomedical conventions (IMRaD, PICO framing where relevant) and "
        "cautious, evidence-graded claims",
    ),
    "life_sciences": (
        "Life Sciences",
        "experimental biology conventions with Materials & Methods, Results, and "
        "Discussion grounded in cited evidence",
    ),
    "agriculture": (
        "Agriculture & Food Science",
        "applied experimental conventions (field/lab trials, treatments, yields) "
        "with Materials & Methods, Results, and Discussion",
    ),
    "environment": (
        "Environmental & Earth Science",
        "systems and sustainability framing with data-driven methods, results, and "
        "policy-relevant discussion",
    ),
    "social_sciences": (
        "Social Sciences",
        "IMRaD with a theoretical framework, clearly stated methodology "
        "(qualitative/quantitative), and findings tied back to theory",
    ),
    "finance": (
        "Finance & Economics",
        "empirical conventions with a literature review, hypotheses, data & "
        "methodology (models/econometrics), findings, and discussion",
    ),
    "business": (
        "Business & Management",
        "empirical/case conventions with a literature review, hypotheses or "
        "propositions, methodology, findings, and managerial implications",
    ),
    "arts": (
        "Arts & Humanities",
        "a thesis-driven, argumentative essay style with close reading/analysis "
        "and interpretive rather than experimental structure",
    ),
    "law": (
        "Law & Policy",
        "doctrinal/analytical structure with issue framing, authorities, analysis, "
        "and policy implications",
    ),
}

DEFAULT_FIELD = "general"


def normalize_field(field: Optional[str]) -> str:
    """Return a known field id, falling back to 'general'."""
    fid = (field or "").strip().lower()
    return fid if fid in FIELD_SOURCES else DEFAULT_FIELD


def sources_for(field: Optional[str]) -> List[str]:
    """Preferred, ordered source list for a field."""
    return FIELD_SOURCES[normalize_field(field)]


def domain_for(field: Optional[str]) -> str:
    """Coarse domain ('cs' | 'health' | 'general') used for result allocation."""
    return _FIELD_DOMAIN.get(normalize_field(field), "general")


def prompt_hint(field: Optional[str], subfield: Optional[str] = None) -> str:
    """One-line discipline hint to prepend to an agent prompt.

    Returns "" for an unknown/general field with no subfield, so callers can add
    the hint unconditionally without polluting prompts when no field was chosen.
    """
    fid = normalize_field(field)
    sub = (subfield or "").strip()
    if fid == DEFAULT_FIELD and not sub:
        return ""
    label, convention = _FIELD_HINT.get(fid, _FIELD_HINT[DEFAULT_FIELD])
    focus = f" (subfield: {sub})" if sub else ""
    return (
        f"Discipline: {label}{focus}. Write for this field — use its conventions, "
        f"terminology, and typical paper structure: {convention}."
    )


def field_from_constraints(constraints: Optional[Dict]) -> tuple[str, str]:
    """Pull (field, subfield) out of a pipeline constraints dict."""
    c = constraints or {}
    return normalize_field(c.get("field")), (c.get("subfield") or "").strip()
