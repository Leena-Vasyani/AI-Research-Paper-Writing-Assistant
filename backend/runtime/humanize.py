"""
Human-in-the-loop humanization metric — single source of truth.

The drafting agent produces machine text; before it flows into review/citation/
formatting we require the author to rewrite a minimum fraction of each *body*
section (default 40%). This module defines that word-change metric and the
per-section quota. It is mirrored byte-for-byte on the frontend
(``web/src/lib/humanize.ts``) but the copy here is authoritative — the
``/api/humanize/validate`` endpoint gates on it so a hand-crafted client cannot
bypass the quota.

Metric (per editable section):
    changed  = len(original_words) - word_lcs(original_words, edited_words)
    required = 0 if len(original_words) < 25 else ceil(fraction * len(original_words))
    met      = changed >= required AND edited keeps >= 50% of the original length

Word-level LCS (not char-Levenshtein) measures how many original words survive
in order: genuine paraphrase (reorder + synonym swap) drops it fast, while
cosmetic churn does not. The length floor is deliberately lenient (50%) so an
author who condenses/tightens a section into fewer words still satisfies the
quota (deletions count as "changed"); it only blocks wholesale deletion of the
section rather than genuine rewriting.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")

DEFAULT_FRACTION = 0.40
MIN_WORDS_TO_REQUIRE = 25
LENGTH_FLOOR_RATIO = 0.50

# Substantive prose roles that must be humanized. Mirrors the "body" grouping in
# drafting_agent.py. Front matter (Abstract) and back matter (Conclusion,
# References) are exempt — editable but not gated.
EDITABLE_ROLES = {"body", "macro_lit_review", "micro_lit_review"}


def tokenize(text: str) -> List[str]:
    """Lowercased word tokens (ignores whitespace/punctuation)."""
    if not text:
        return []
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def word_lcs_len(a: List[str], b: List[str]) -> int:
    """Length of the longest common subsequence of two token lists.

    O(len(a) * len(b)) time, O(min) memory via a single rolling row.
    """
    if not a or not b:
        return 0
    # Iterate the longer list on the outer loop, keep the shorter as the row.
    if len(b) > len(a):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for token_a in a:
        curr = [0] * (len(b) + 1)
        for j, token_b in enumerate(b, start=1):
            if token_a == token_b:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = curr[j - 1] if curr[j - 1] >= prev[j] else prev[j]
        prev = curr
    return prev[len(b)]


def changed_words(original: str, edited: str) -> int:
    """How many original words were substituted or deleted."""
    o = tokenize(original)
    e = tokenize(edited)
    if not o:
        return len(e)
    return len(o) - word_lcs_len(o, e)


def required_changes(original: str, fraction: float = DEFAULT_FRACTION) -> int:
    """Words the author must change; 0 for very short sections."""
    n = len(tokenize(original))
    if n < MIN_WORDS_TO_REQUIRE:
        return 0
    return math.ceil(fraction * n)


def is_editable(role: Optional[str]) -> bool:
    """Only substantive body-prose roles are gated."""
    return (role or "") in EDITABLE_ROLES


def section_stats(
    name: str,
    original: str,
    edited: str,
    fraction: float = DEFAULT_FRACTION,
    role: Optional[str] = None,
) -> Dict[str, Any]:
    """Full per-section quota status."""
    o = tokenize(original)
    e = tokenize(edited)
    editable = is_editable(role)
    original_words = len(o)
    edited_words = len(e)
    changed = edited_words if original_words == 0 else original_words - word_lcs_len(o, e)
    required = 0 if original_words < MIN_WORDS_TO_REQUIRE else math.ceil(fraction * original_words)
    length_floor = math.floor(LENGTH_FLOOR_RATIO * original_words)
    length_ok = (not editable) or original_words == 0 or edited_words >= length_floor
    met = (not editable) or (changed >= required and length_ok)
    return {
        "name": name,
        "editable": editable,
        "role": role or "",
        "original_words": original_words,
        "edited_words": edited_words,
        "changed": changed,
        "required": required,
        "length_floor": length_floor,
        "length_ok": length_ok,
        "met": met,
    }


def _role_map(blueprint: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """name -> role from the blueprint (exact + lowercase keys)."""
    roles: Dict[str, str] = {}
    for spec in (blueprint or {}).get("sections", []) or []:
        name = spec.get("name")
        if not name:
            continue
        role = spec.get("role", "body")
        roles[name] = role
        roles[name.strip().lower()] = role
    return roles


def _role_for(name: str, roles: Dict[str, str]) -> Optional[str]:
    if name in roles:
        return roles[name]
    return roles.get(name.strip().lower())


def build_humanize_meta(
    sections: Dict[str, str],
    fraction: float = DEFAULT_FRACTION,
    blueprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Per-section editability + quota target, stamped onto the draft for the UI."""
    roles = _role_map(blueprint)
    meta_sections: Dict[str, Any] = {}
    for name, text in (sections or {}).items():
        role = _role_for(name, roles)
        editable = is_editable(role)
        n = len(tokenize(text or ""))
        meta_sections[name] = {
            "editable": editable,
            "role": role or "",
            "original_words": n,
            "required": 0 if n < MIN_WORDS_TO_REQUIRE else math.ceil(fraction * n),
            "length_floor": math.floor(LENGTH_FLOOR_RATIO * n),
        }
    return {"fraction": fraction, "sections": meta_sections}


def validate_quota(
    original_sections: Dict[str, str],
    edited_sections: Dict[str, str],
    fraction: float = DEFAULT_FRACTION,
    blueprint: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return the stats of every editable section that has NOT met its quota.

    An empty list means every gated section passed.
    """
    roles = _role_map(blueprint)
    failures: List[Dict[str, Any]] = []
    for name, original in (original_sections or {}).items():
        role = _role_for(name, roles)
        if not is_editable(role):
            continue
        stats = section_stats(
            name,
            original,
            (edited_sections or {}).get(name, ""),
            fraction=fraction,
            role=role,
        )
        if not stats["met"]:
            failures.append(stats)
    return failures
