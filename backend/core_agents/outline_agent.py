"""
Outline Agent — produces the JSON Blueprint that drives the Drafting Agent.

Mirrors the architecture diagram's Outline flow:
    Generate Section Cues (small model)
      -> Draft section plan (large model)
      -> Check via Delta Feedback (coverage refinement)
      -> Enhance Cues loop

Design principle: a deterministic skeleton is ALWAYS produced first (so the
pipeline yields a valid blueprint offline / when the LLM is unavailable), then
LLM output is layered on top to enrich cues, subsections, citation hints, and
visualization directives. The delta-feedback pass guarantees every theme and
coverage gap is mapped into some section.

Blueprint contract (consumed by the Drafting Agent in Phase 4):

    {
      "topic", "target_venue", "output_type", "title_hint",
      "sections": [
        {
          "name", "role",              # role: front_matter|macro_lit_review|
                                       #       micro_lit_review|body|back_matter
          "goal",
          "target_words",
          "subsections": [{"name", "cues": [...], "target_words"}],
          "citation_hints": [{"claim", "suggested_sources": [...]}],
          "visualization_directives": [{"type", "description"}],
        }, ...
      ],
      "themes", "gaps",
      "lit_review": {"macro": "Introduction", "micro": "Related Work"},
      "meta": {"method", "revisions", "coverage"}
    }
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

_WORD_RE = re.compile(r"[a-z0-9]+")
_SECTION_RE = re.compile(r"\\(?:sub)?section\*?\{([^}]+)\}")


# ---------------------------------------------------------------------------
# Default section structures per output type
# (name, role, n_subsections, target_words)
# ---------------------------------------------------------------------------

_STRUCTURES: Dict[str, List[Tuple[str, str, int, int]]] = {
    "research_paper": [
        ("Abstract", "front_matter", 0, 200),
        ("Introduction", "macro_lit_review", 3, 900),
        ("Related Work", "micro_lit_review", 3, 800),
        ("Methodology", "body", 4, 1000),
        ("Experiments and Results", "body", 3, 1000),
        ("Discussion", "body", 3, 800),
        ("Conclusion", "back_matter", 0, 400),
        ("References", "back_matter", 0, 0),
    ],
    "survey": [
        ("Abstract", "front_matter", 0, 250),
        ("Introduction", "macro_lit_review", 3, 1000),
        ("Background", "micro_lit_review", 3, 900),
        ("Taxonomy of Approaches", "body", 4, 1200),
        ("Comparative Analysis", "body", 4, 1100),
        ("Open Challenges", "body", 3, 800),
        ("Future Directions", "body", 2, 700),
        ("Conclusion", "back_matter", 0, 400),
        ("References", "back_matter", 0, 0),
    ],
}
_STRUCTURES["report"] = _STRUCTURES["research_paper"]


class OutlineAgent:
    def __init__(self, use_llm: bool = True, max_subsections: int = 4):
        self.use_llm = use_llm
        self.max_subsections = max_subsections

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        topic: str,
        *,
        themes: Optional[Dict[str, Any]] = None,
        corpus: Optional[List[Dict[str, Any]]] = None,
        citation_graph: Optional[Dict[str, Any]] = None,
        target_venue: str = "IEEE",
        output_type: str = "research_paper",
        raw_materials: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        themes = themes or {}
        corpus = corpus or []
        citation_graph = citation_graph or {}
        raw_materials = raw_materials or {}

        clusters = themes.get("clusters", []) or []
        gaps = themes.get("gaps", []) or []

        # 1. Structure: template (if provided) overrides the default skeleton.
        template = raw_materials.get("latex_template") or ""
        section_specs = self._structure_from_template(template) or self._default_structure(output_type)

        # 2. Deterministic skeleton (always valid).
        blueprint = self._skeleton(
            topic, target_venue, output_type, section_specs, clusters, gaps, corpus, citation_graph
        )

        method = "deterministic"
        # 3. Generate cues (small model) -> enrich (large model).
        if self.use_llm:
            cues = self._llm_section_cues(topic, blueprint, clusters, gaps)
            enriched = self._llm_enrich(topic, target_venue, blueprint, cues, clusters, gaps, corpus)
            if enriched:
                blueprint = enriched
                method = "llm_enriched"

        # 4. Delta-feedback coverage refinement (always runs).
        blueprint, revisions, coverage = self._delta_feedback(blueprint, clusters, gaps)

        blueprint["meta"] = {"method": method, "revisions": revisions, "coverage": coverage}
        return blueprint

    # ------------------------------------------------------------------
    # Structure
    # ------------------------------------------------------------------

    def _default_structure(self, output_type: str) -> List[Tuple[str, str, int, int]]:
        return _STRUCTURES.get(output_type, _STRUCTURES["research_paper"])

    def _structure_from_template(self, latex_template: str) -> Optional[List[Tuple[str, str, int, int]]]:
        """Parse \\section{...} names from a conference LaTeX template."""
        if not latex_template:
            return None
        names = [n.strip() for n in _SECTION_RE.findall(latex_template) if n.strip()]
        if not names:
            return None
        specs: List[Tuple[str, str, int, int]] = []
        for name in names:
            role = self._infer_role(name)
            words = 200 if role == "front_matter" else 0 if name.lower() == "references" else 900
            n_sub = 0 if role in ("front_matter", "back_matter") else self.max_subsections
            specs.append((name, role, n_sub, words))
        return specs

    @staticmethod
    def _infer_role(name: str) -> str:
        low = name.lower()
        if "abstract" in low:
            return "front_matter"
        if low.startswith("introduction"):
            return "macro_lit_review"
        if "related work" in low or "background" in low or "literature" in low:
            return "micro_lit_review"
        if "conclusion" in low or "reference" in low or "acknowledg" in low:
            return "back_matter"
        return "body"

    # ------------------------------------------------------------------
    # Deterministic skeleton
    # ------------------------------------------------------------------

    def _skeleton(
        self,
        topic: str,
        venue: str,
        output_type: str,
        section_specs: List[Tuple[str, str, int, int]],
        clusters: List[Dict[str, Any]],
        gaps: List[str],
        corpus: List[Dict[str, Any]],
        citation_graph: Dict[str, Any],
    ) -> Dict[str, Any]:
        macro = next((n for n, r, *_ in section_specs if r == "macro_lit_review"), "Introduction")
        micro = next((n for n, r, *_ in section_specs if r == "micro_lit_review"), "Related Work")

        sections: List[Dict[str, Any]] = []
        for idx, (name, role, n_sub, words) in enumerate(section_specs):
            subsections = self._default_subsections(name, role, n_sub, clusters, words)
            sections.append({
                "name": name,
                "role": role,
                "goal": self._section_goal(name, role, topic),
                "target_words": words,
                "subsections": subsections,
                "citation_hints": self._citation_hints(role, clusters, corpus, citation_graph),
                "visualization_directives": self._viz_directives(name, role),
            })

        return {
            "topic": topic,
            "target_venue": venue,
            "output_type": output_type,
            "title_hint": topic.strip().title(),
            "sections": sections,
            "themes": [c.get("theme", "") for c in clusters],
            "gaps": list(gaps),
            "lit_review": {"macro": macro, "micro": micro},
        }

    def _default_subsections(
        self, name: str, role: str, n_sub: int, clusters: List[Dict[str, Any]], words: int
    ) -> List[Dict[str, Any]]:
        if n_sub <= 0:
            return []
        per = max(150, words // max(1, n_sub)) if words else 250
        # For lit-review sections, seed subsections from discovered themes.
        if role in ("macro_lit_review", "micro_lit_review") and clusters:
            picked = clusters[:n_sub]
            return [
                {"name": c.get("theme", f"Theme {i+1}"),
                 "cues": [f"Synthesize work on {c.get('theme', '')}"],
                 "target_words": per}
                for i, c in enumerate(picked)
            ]
        return [
            {"name": f"{name} — part {i+1}", "cues": [], "target_words": per}
            for i in range(n_sub)
        ]

    @staticmethod
    def _section_goal(name: str, role: str, topic: str) -> str:
        goals = {
            "front_matter": f"Concise framing of '{topic}' and its contributions.",
            "macro_lit_review": f"Motivate '{topic}', state the problem and contributions, broad context.",
            "micro_lit_review": f"Position against prior work most relevant to '{topic}'.",
            "body": f"Present the substantive content of {name} for '{topic}'.",
            "back_matter": f"Close out {name} for '{topic}'.",
        }
        return goals.get(role, f"Write the {name} section.")

    def _citation_hints(
        self, role: str, clusters: List[Dict[str, Any]],
        corpus: List[Dict[str, Any]], citation_graph: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if role not in ("macro_lit_review", "micro_lit_review", "body"):
            return []
        # Prefer the most-cited nodes from the citation graph; fall back to corpus.
        nodes = citation_graph.get("nodes") or []
        ranked = sorted(nodes, key=lambda n: n.get("citations", 0), reverse=True)
        titles = [n.get("title", "") for n in ranked[:5] if n.get("title")]
        if not titles:
            titles = [p.get("title", "") for p in corpus[:5] if p.get("title")]
        if not titles:
            return []
        claim = ("Establish the state of the art" if role != "body"
                 else "Ground methodological/experimental claims")
        return [{"claim": claim, "suggested_sources": titles}]

    @staticmethod
    def _viz_directives(name: str, role: str) -> List[Dict[str, Any]]:
        low = name.lower()
        if "result" in low or "experiment" in low or "comparative" in low:
            return [
                {"type": "table", "description": "Quantitative results / comparison table"},
                {"type": "plot", "description": "Performance comparison across methods"},
            ]
        if "method" in low or "taxonomy" in low:
            return [{"type": "figure", "description": "Architecture / approach diagram"}]
        return []

    # ------------------------------------------------------------------
    # LLM cue generation + enrichment (graceful, optional)
    # ------------------------------------------------------------------

    def _llm_section_cues(
        self, topic: str, blueprint: Dict[str, Any],
        clusters: List[Dict[str, Any]], gaps: List[str],
    ) -> Dict[str, List[str]]:
        try:
            from backend.runtime.models import small_model
        except Exception:
            return {}
        section_names = [s["name"] for s in blueprint["sections"]
                         if s["role"] not in ("back_matter",)]
        theme_list = ", ".join(c.get("theme", "") for c in clusters) or "n/a"
        gap_list = "; ".join(gaps) or "n/a"
        prompt = (
            f"You are planning an academic paper on: \"{topic}\".\n"
            f"Discovered themes: {theme_list}\nKnown gaps: {gap_list}\n"
            f"For EACH section below, give 2-3 short writing cues (imperative phrases).\n"
            f"Sections: {', '.join(section_names)}\n"
            "Return ONLY JSON: an object mapping section name -> list of cue strings."
        )
        raw = small_model(prompt, max_tokens=600, temperature=0.3)
        data = _extract_json(raw)
        if isinstance(data, dict):
            return {k: [str(c) for c in v][:3] for k, v in data.items() if isinstance(v, list)}
        return {}

    def _llm_enrich(
        self, topic: str, venue: str, blueprint: Dict[str, Any],
        cues: Dict[str, List[str]], clusters: List[Dict[str, Any]],
        gaps: List[str], corpus: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        # Merge small-model cues into the deterministic skeleton (no extra call
        # needed if cues exist; this keeps the blueprint valid and grounded).
        if not cues:
            return None
        enriched = json.loads(json.dumps(blueprint))  # deep copy
        for section in enriched["sections"]:
            section_cues = cues.get(section["name"])
            if not section_cues:
                continue
            if section["subsections"]:
                # distribute cues across subsections
                for i, sub in enumerate(section["subsections"]):
                    extra = section_cues[i % len(section_cues)]
                    if extra not in sub["cues"]:
                        sub["cues"].append(extra)
            else:
                section.setdefault("cues", [])
                section["cues"] = section_cues
        return enriched

    # ------------------------------------------------------------------
    # Delta-feedback coverage refinement
    # ------------------------------------------------------------------

    def _delta_feedback(
        self, blueprint: Dict[str, Any],
        clusters: List[Dict[str, Any]], gaps: List[str],
    ) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
        """Ensure every theme and gap is referenced somewhere; patch if not.

        Coverage is measured against the *section plan* only (not the top-level
        themes/gaps summary lists, which would otherwise always match).
        """
        revisions = 0

        def _sections_blob() -> str:
            return json.dumps(blueprint.get("sections", [])).lower()

        text_blob = _sections_blob()

        # Themes not mentioned anywhere -> add to the micro lit-review section.
        micro_name = blueprint.get("lit_review", {}).get("micro", "Related Work")
        body_name = next((s["name"] for s in blueprint["sections"] if s["role"] == "body"), None)

        uncovered_themes = [
            c.get("theme", "") for c in clusters
            if c.get("theme") and c["theme"].lower() not in text_blob
        ]
        if uncovered_themes:
            target = _find_section(blueprint, micro_name) or _find_section(blueprint, body_name)
            if target is not None:
                target.setdefault("subsections", [])
                for theme in uncovered_themes:
                    target["subsections"].append({
                        "name": theme, "cues": [f"Cover {theme}"], "target_words": 200,
                    })
                    revisions += 1

        # Gaps not referenced -> add as Discussion/Future cues.
        uncovered_gaps = [g for g in gaps if g.lower() not in _sections_blob()]
        if uncovered_gaps:
            disc = (_find_section(blueprint, "Discussion")
                    or _find_section(blueprint, "Open Challenges")
                    or (_find_section(blueprint, body_name) if body_name else None))
            if disc is not None:
                disc.setdefault("cues", [])
                for g in uncovered_gaps:
                    disc["cues"].append(f"Address gap: {g}")
                    revisions += 1

        coverage = {
            "themes_total": len(clusters),
            "themes_uncovered_before": len(uncovered_themes),
            "gaps_total": len(gaps),
            "gaps_uncovered_before": len(uncovered_gaps),
        }
        return blueprint, revisions, coverage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_section(blueprint: Dict[str, Any], name: Optional[str]) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    for section in blueprint.get("sections", []):
        if section.get("name") == name:
            return section
    return None


def _extract_json(text: Optional[str]) -> Any:
    """Best-effort JSON extraction from an LLM response (handles code fences)."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    # find the first balanced {...} or [...]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                continue
    return None
