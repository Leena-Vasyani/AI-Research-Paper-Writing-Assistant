"""
Phase 6 tests for the Formatter Agent.
"""

import unittest

from backend.core_agents.formatter_agent import FormatterAgent
from backend.core_agents.outline_agent import OutlineAgent


class FormatterAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = FormatterAgent(generate_diagrams=False)
        self.blueprint = OutlineAgent(use_llm=False).build(
            "smart grid forecasting",
            themes={"clusters": [{"theme": "load forecasting"}], "gaps": []},
        )
        self.draft = {
            "title": "Smart Grid Forecasting",
            "sections": {"Abstract": "An abstract.", "Methodology": "We do X.",
                         "Experiments and Results": "We achieve good results."},
            "latex": "",  # force the formatter to render
            "references_used": [{"title": "Prior Work", "authors_str": "A. B", "published": "2022"}],
        }

    def test_markdown_export(self):
        out = self.agent.format(self.draft, self.blueprint, output_formats=("markdown",))
        md = out["formats"]["markdown"]
        self.assertIn("# Smart Grid Forecasting", md)
        self.assertIn("## Methodology", md)
        self.assertIn("## References", md)

    def test_latex_export_built_when_missing(self):
        out = self.agent.format(self.draft, self.blueprint, output_formats=("latex",))
        latex = out["formats"]["latex"]
        self.assertIn("\\documentclass", latex)
        self.assertIn("\\begin{abstract}", latex)
        self.assertIn("\\section{Methodology}", latex)

    def test_figures_collected_from_blueprint(self):
        out = self.agent.format(self.draft, self.blueprint)
        figs = out["figures"]
        self.assertTrue(figs)
        # blueprint puts a table+plot on Results and a figure on Methodology
        kinds = {f["type"] for f in figs}
        self.assertTrue(kinds & {"table", "plot", "figure"})

    def test_references_from_citation_result(self):
        citation_result = {
            "cited_draft": {"Abstract": "An abstract [1]."},
            "references": [{"reference": "[1] A. B, \"Prior Work,\" 2022."}],
        }
        out = self.agent.format(self.draft, self.blueprint, citation_result=citation_result)
        self.assertEqual(out["references"][0], "[1] A. B, \"Prior Work,\" 2022.")
        # cited sections preferred over raw draft sections
        self.assertIn("Abstract", out["sections"])

    def test_latex_renders_table_and_figure_floats(self):
        out = self.agent.format(self.draft, self.blueprint, output_formats=("latex",))
        latex = out["formats"]["latex"]
        # blueprint puts a table+plot on Results and a figure on Methodology
        self.assertIn("\\begin{table}", latex)
        self.assertIn("\\begin{figure}", latex)
        self.assertIn("\\caption{", latex)

    def test_latex_uses_cited_sections_and_formatted_refs(self):
        citation_result = {
            "cited_draft": {"Methodology": "We use a method [1].", "Abstract": "An abstract."},
            "references": [{"reference": '[1] A. B, "Prior Work," 2022.'}],
        }
        # draft has a stale pre-citation latex that must NOT be reused
        draft = dict(self.draft, latex="\\documentclass{article}STALE")
        out = self.agent.format(draft, self.blueprint, citation_result=citation_result, output_formats=("latex",))
        latex = out["formats"]["latex"]
        self.assertNotIn("STALE", latex)          # fresh render, not the draft's latex
        self.assertIn("[1]", latex)               # inline citation preserved
        self.assertIn("thebibliography", latex)
        self.assertIn("Prior Work", latex)        # formatted reference present

    def test_export_ready_reflects_grounding(self):
        out = self.agent.format(
            self.draft, self.blueprint,
            grounding={"export_ready": False, "blocked": [{"claim": "x"}]},
        )
        self.assertFalse(out["export_ready"])


if __name__ == "__main__":
    unittest.main()
