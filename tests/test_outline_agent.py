"""
Phase 3 tests for the Outline Agent.

Run with use_llm=False so no model loads / no network — they exercise the
deterministic skeleton, template parsing, citation hints, and the
delta-feedback coverage pass.
"""

import unittest

from backend.core_agents.outline_agent import OutlineAgent, _extract_json


def _themes(theme_names, gaps=None):
    return {
        "clusters": [{"theme": t, "keywords": [t.split()[0]], "size": 2} for t in theme_names],
        "gaps": gaps or [],
    }


class OutlineSkeletonTest(unittest.TestCase):
    def setUp(self):
        self.agent = OutlineAgent(use_llm=False)

    def test_research_paper_structure(self):
        bp = self.agent.build("graph neural networks for smart grids",
                              themes=_themes(["GNN models", "load forecasting"]))
        names = [s["name"] for s in bp["sections"]]
        self.assertIn("Introduction", names)
        self.assertIn("Related Work", names)
        self.assertIn("References", names)
        self.assertEqual(bp["lit_review"], {"macro": "Introduction", "micro": "Related Work"})
        # roles assigned
        intro = next(s for s in bp["sections"] if s["name"] == "Introduction")
        self.assertEqual(intro["role"], "macro_lit_review")
        self.assertEqual(bp["meta"]["method"], "deterministic")

    def test_lit_review_subsections_seeded_from_themes(self):
        bp = self.agent.build("topic", themes=_themes(["theme alpha", "theme beta"]))
        related = next(s for s in bp["sections"] if s["name"] == "Related Work")
        sub_names = [s["name"] for s in related["subsections"]]
        self.assertIn("theme alpha", sub_names)

    def test_template_overrides_structure(self):
        template = r"\section{Intro}\section{Our Method}\section{Evaluation}\section{Conclusion}"
        bp = self.agent.build("t", themes=_themes(["x"]),
                              raw_materials={"latex_template": template})
        names = [s["name"] for s in bp["sections"]]
        self.assertEqual(names, ["Intro", "Our Method", "Evaluation", "Conclusion"])

    def test_citation_hints_prefer_most_cited(self):
        cg = {"nodes": [
            {"title": "Highly Cited Paper", "citations": 500},
            {"title": "Less Cited", "citations": 3},
        ]}
        bp = self.agent.build("t", themes=_themes(["x"]), citation_graph=cg)
        related = next(s for s in bp["sections"] if s["name"] == "Related Work")
        hints = related["citation_hints"]
        self.assertTrue(hints)
        self.assertEqual(hints[0]["suggested_sources"][0], "Highly Cited Paper")

    def test_delta_feedback_covers_extra_themes_and_gaps(self):
        # 5 themes: only first 3 seed lit-review subsections -> themes 4,5 uncovered.
        themes = _themes(
            ["alpha one", "beta two", "gamma three", "delta four", "epsilon five"],
            gaps=["no long horizon evaluation"],
        )
        bp = self.agent.build("t", themes=themes)
        self.assertGreaterEqual(bp["meta"]["revisions"], 2)
        blob = str(bp).lower()
        self.assertIn("delta four", blob)
        self.assertIn("epsilon five", blob)
        self.assertIn("no long horizon evaluation", blob)
        self.assertEqual(bp["meta"]["coverage"]["gaps_total"], 1)


class ExtractJsonTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_extract_json('{"a": 1}'), {"a": 1})

    def test_code_fence(self):
        self.assertEqual(_extract_json('```json\n{"a": [1,2]}\n```'), {"a": [1, 2]})

    def test_embedded(self):
        self.assertEqual(_extract_json('here you go: {"x": "y"} thanks'), {"x": "y"})

    def test_garbage_returns_none(self):
        self.assertIsNone(_extract_json("not json at all"))


if __name__ == "__main__":
    unittest.main()
