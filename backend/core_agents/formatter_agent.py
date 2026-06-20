"""
Formatter Agent — assembles the final exportable artifact.

Unifies the export concerns scattered across the old codebase (LaTeX/IEEE
formatting, Markdown, diagram + pseudocode hooks) into a single stage that
consumes the cited draft + the blueprint and produces:

  - LaTeX (reuses the Drafting Agent's render, or builds one)
  - Markdown
  - a consolidated reference list
  - figure / plot directives gathered from the blueprint (for the UI / Plotting)
  - export-readiness from the citation grounding gate

Diagram generation (Mermaid via the DiagramAgent) is available behind a flag
but off by default so the formatter performs no LLM calls in the default path.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FormatterAgent:
    def __init__(self, generate_diagrams: bool = False):
        self.generate_diagrams = generate_diagrams

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(
        self,
        draft: Dict[str, Any],
        blueprint: Optional[Dict[str, Any]] = None,
        *,
        citation_result: Optional[Dict[str, Any]] = None,
        grounding: Optional[Dict[str, Any]] = None,
        review: Optional[Dict[str, Any]] = None,
        output_formats=("latex", "markdown"),
    ) -> Dict[str, Any]:
        blueprint = blueprint or {}
        draft = draft or {}
        citation_result = citation_result or {}
        grounding = grounding or citation_result.get("grounding") or {}

        title = draft.get("title") or blueprint.get("title_hint") or blueprint.get("topic", "")
        sections = self._resolve_sections(draft, citation_result)
        references = self._references(citation_result, draft)
        figures = self._collect_figures(blueprint)

        if self.generate_diagrams:
            self._render_diagrams(figures)

        artifacts: Dict[str, Any] = {}
        if "latex" in output_formats:
            artifacts["latex"] = draft.get("latex") or self._to_latex(
                title, sections, blueprint, references
            )
        if "markdown" in output_formats:
            artifacts["markdown"] = self._to_markdown(title, sections, references, figures)
        if "docx" in output_formats:
            # DOCX/PDF rendering is delegated to the existing compile pipeline;
            # the markdown/latex here are the canonical sources for it.
            artifacts["docx_available"] = True

        export_ready = bool(grounding.get("export_ready", True))
        return {
            "title": title,
            "output_type": blueprint.get("output_type", "research_paper"),
            "target_venue": blueprint.get("target_venue", "IEEE"),
            "sections": sections,
            "references": references,
            "figures": figures,
            "formats": artifacts,
            "export_ready": export_ready,
            "grounding": grounding,
            "review": review or {},
        }

    # ------------------------------------------------------------------
    # Section / reference resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_sections(draft: Dict[str, Any], citation_result: Dict[str, Any]) -> Dict[str, str]:
        """Prefer the cited section text; fall back to the raw draft sections."""
        cited = citation_result.get("cited_draft")
        if isinstance(cited, dict) and cited:
            return {k: v for k, v in cited.items() if k.lower() != "references"}
        return draft.get("sections", {}) or {}

    @staticmethod
    def _references(citation_result: Dict[str, Any], draft: Dict[str, Any]) -> List[str]:
        refs = citation_result.get("references")
        out: List[str] = []
        if isinstance(refs, list):
            for r in refs:
                if isinstance(r, str):
                    out.append(r)
                elif isinstance(r, dict):
                    out.append(r.get("reference") or r.get("formatted") or
                               (r.get("paper_info") or {}).get("title", ""))
        if out:
            return [r for r in out if r]
        # fall back to references_used from drafting
        used = draft.get("references_used", [])
        return [
            f"{p.get('authors_str') or 'Unknown'}, \"{p.get('title', '')},\" {p.get('published', '')}."
            for p in used if p.get("title")
        ]

    # ------------------------------------------------------------------
    # Figure / plot directives
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_figures(blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
        figures: List[Dict[str, Any]] = []
        for section in blueprint.get("sections", []) or []:
            for directive in section.get("visualization_directives", []) or []:
                figures.append({
                    "section": section.get("name", ""),
                    "type": directive.get("type", "figure"),
                    "description": directive.get("description", ""),
                    "rendered": None,  # filled by _render_diagrams when enabled
                })
        return figures

    def _render_diagrams(self, figures: List[Dict[str, Any]]) -> None:
        """Optional: turn 'figure' directives into Mermaid via the DiagramAgent."""
        try:
            from backend.core_agents.diagram_agent import DiagramAgent
            agent = DiagramAgent()
        except Exception:
            return
        for fig in figures:
            if fig["type"] != "figure" or not fig.get("description"):
                continue
            try:
                result = agent.generate_diagram(fig["description"])  # type: ignore[attr-defined]
                if isinstance(result, dict):
                    fig["rendered"] = result.get("mermaid_code")
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def _to_markdown(
        self, title: str, sections: Dict[str, str],
        references: List[str], figures: List[Dict[str, Any]],
    ) -> str:
        parts = [f"# {title}\n"]
        for name, text in sections.items():
            parts.append(f"## {name}\n\n{text}\n")
        if figures:
            parts.append("## Figures\n")
            for i, f in enumerate(figures, 1):
                parts.append(f"- **Figure {i}** ({f['type']}, {f['section']}): {f['description']}")
            parts.append("")
        if references:
            parts.append("## References\n")
            for i, ref in enumerate(references, 1):
                parts.append(f"{i}. {ref}")
        return "\n".join(parts)

    def _to_latex(
        self, title: str, sections: Dict[str, str],
        blueprint: Dict[str, Any], references: List[str],
    ) -> str:
        venue = blueprint.get("target_venue", "IEEE")
        documentclass = "IEEEtran" if "ieee" in str(venue).lower() else "article"
        spec_roles = {s.get("name", ""): s.get("role", "body")
                      for s in blueprint.get("sections", [])}
        lines = [
            f"\\documentclass[conference]{{{documentclass}}}",
            "\\usepackage{graphicx}\n\\usepackage{cite}",
            "\\begin{document}",
            f"\\title{{{_tex(title)}}}",
            "\\maketitle",
        ]
        for name, text in sections.items():
            if spec_roles.get(name) == "front_matter" and name.lower() == "abstract":
                lines.append(f"\\begin{{abstract}}\n{_tex(text)}\n\\end{{abstract}}")
            else:
                lines.append(f"\\section{{{_tex(name)}}}\n{_tex(text)}")
        if references:
            lines.append("\\begin{thebibliography}{99}")
            for i, ref in enumerate(references, 1):
                lines.append(f"\\bibitem{{ref{i}}} {_tex(ref)}")
            lines.append("\\end{thebibliography}")
        lines.append("\\end{document}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------

def _tex(text: str) -> str:
    if not text:
        return ""
    for ch, rep in {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }.items():
        text = text.replace(ch, rep)
    return text
