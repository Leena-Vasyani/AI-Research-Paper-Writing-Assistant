"""
Phase 4 tests for the Drafting Agent.

Offline + deterministic: use_llm=False (no model/network for generation) and the
embedding model is patched off so retrieval uses the lexical fallback.
"""

import unittest

import backend.core_agents.drafting_agent as drafting_mod
from backend.core_agents.drafting_agent import DraftingAgent
from backend.core_agents.outline_agent import OutlineAgent


def _corpus(n=8):
    topics = ["graph neural network", "load forecasting", "reinforcement learning",
              "battery storage", "demand response", "solar power", "wind energy",
              "energy management"]
    return [
        {"title": f"{topics[i % len(topics)].title()} study {i}",
         "abstract": f"A paper about {topics[i % len(topics)]} for power systems.",
         "authors_str": "A. Author", "published": "2023"}
        for i in range(n)
    ]


class DraftingAgentTest(unittest.TestCase):
    def setUp(self):
        # Force lexical retrieval (no embedding model load) for fast determinism.
        self._orig_embed = drafting_mod._get_embed_model
        drafting_mod._get_embed_model = lambda: None
        self.blueprint = OutlineAgent(use_llm=False).build(
            "graph neural networks for smart grids",
            themes={"clusters": [{"theme": "GNN forecasting"}, {"theme": "RL control"}],
                    "gaps": ["no topology-shift ablation"]},
        )
        self.agent = DraftingAgent(use_llm=False, ref_cap_fraction=0.25)

    def tearDown(self):
        drafting_mod._get_embed_model = self._orig_embed

    def test_produces_all_sections_except_references(self):
        corpus = _corpus(8)
        result = self.agent.draft(self.blueprint, corpus, topic="GNNs for smart grids")
        names = list(result["sections"].keys())
        self.assertIn("Introduction", names)
        self.assertIn("Methodology", names)
        self.assertIn("Abstract", names)
        self.assertIn("Conclusion", names)
        self.assertNotIn("References", names)  # auto-generated downstream
        # every section has non-empty prose
        for name, text in result["sections"].items():
            self.assertTrue(text.strip(), f"empty section: {name}")
        self.assertEqual(result["method"], "deterministic")

    def test_reference_cap_25_percent(self):
        corpus = _corpus(8)  # cap = round(0.25*8) = 2
        result = self.agent.draft(self.blueprint, corpus, topic="t")
        for name, meta in result["section_meta"].items():
            self.assertLessEqual(len(meta["refs_used"]), 2,
                                 f"{name} exceeded ref cap: {meta['refs_used']}")

    def test_body_first_ordering(self):
        corpus = _corpus(4)
        result = self.agent.draft(self.blueprint, corpus, topic="t")
        order = result["ordering"]
        # blueprint order is preserved (Abstract appears, References removed)
        self.assertEqual(order[0], "Abstract")
        self.assertIn("Conclusion", order)
        self.assertNotIn("References", order)

    def test_latex_render_structure(self):
        result = self.agent.draft(self.blueprint, _corpus(4), topic="t")
        latex = result["latex"]
        self.assertIn("\\documentclass", latex)
        self.assertIn("\\title{", latex)
        self.assertIn("\\begin{abstract}", latex)
        self.assertIn("\\section{", latex)
        self.assertIn("\\begin{thebibliography}", latex)
        self.assertIn("\\end{document}", latex)

    def test_title_fallback_to_blueprint(self):
        result = self.agent.draft(self.blueprint, [], topic="GNNs for smart grids")
        self.assertEqual(result["title"], self.blueprint["title_hint"])

    def test_verify_section_flags_short_text(self):
        spec = {"name": "Methodology", "role": "body", "target_words": 1000}
        ok, issues = self.agent._verify_section(spec, "too short.", [])
        self.assertFalse(ok)
        self.assertTrue(any("short" in i for i in issues))

    def test_model_routing_per_section(self):
        from backend.runtime.models import small_model, large_model
        # Abstract/Conclusion → small model; body/lit-review → large model
        self.assertIs(self.agent._model_for_section({"name": "Abstract", "role": "front_matter"}), small_model)
        self.assertIs(self.agent._model_for_section({"name": "Conclusion", "role": "back_matter"}), small_model)
        self.assertIs(self.agent._model_for_section({"name": "Methodology", "role": "body"}), large_model)
        self.assertIs(self.agent._model_for_section({"name": "Related Work", "role": "micro_lit_review"}), large_model)

    def test_shared_context_includes_plan(self):
        ctx = self.agent._build_shared_context(self.blueprint, "GNNs for smart grids", ["GNN", "load forecasting"])
        self.assertIn("Section plan", ctx)
        self.assertIn("terminology", ctx.lower())


if __name__ == "__main__":
    unittest.main()
