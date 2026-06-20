"""
Phase 6 tests for the Citation Agent grounding gate.
"""

import unittest

from backend.core_agents.citation_agent import CitationAgent


class GroundingGateTest(unittest.TestCase):
    def setUp(self):
        self.agent = CitationAgent()

    def test_blocked_when_no_supporting_source(self):
        draft = {"Results": "Our method achieves 95% accuracy and outperforms all baselines."}
        result = self.agent.ground_draft(draft, retrieved_papers=[])
        g = result["grounding"]
        self.assertGreaterEqual(g["total_claims"], 1)
        self.assertTrue(g["blocked"])
        self.assertFalse(g["export_ready"])

    def test_inline_citation_counts_as_grounded(self):
        draft = {"Results": "Our method achieves 95% accuracy and outperforms baselines [1]."}
        result = self.agent.ground_draft(draft, retrieved_papers=[])
        g = result["grounding"]
        self.assertEqual(g["total_claims"], 1)
        self.assertEqual(g["grounded"], 1)
        self.assertTrue(g["export_ready"])

    def test_non_factual_sentences_not_counted(self):
        draft = {"Introduction": "This paper discusses an interesting and broad topic area."}
        result = self.agent.ground_draft(draft, retrieved_papers=[])
        self.assertEqual(result["grounding"]["total_claims"], 0)
        self.assertTrue(result["grounding"]["export_ready"])

    def test_is_factual_claim_detection(self):
        self.assertTrue(self.agent._is_factual_claim("We reach 90% accuracy."))
        self.assertTrue(self.agent._is_factual_claim("It outperforms the baseline."))
        self.assertFalse(self.agent._is_factual_claim("The topic is interesting."))

    def test_grounded_when_relevant_source_exists(self):
        draft = {"Results": "The model improves forecasting accuracy on smart grid load data."}
        papers = [{
            "title": "Forecasting Smart Grid Load with Neural Networks",
            "abstract": "We improve forecasting accuracy on smart grid load data using neural networks.",
            "authors_str": "A. Author", "published": "2023",
        }]
        result = self.agent.ground_draft(draft, retrieved_papers=papers)
        g = result["grounding"]
        self.assertEqual(g["total_claims"], 1)
        self.assertEqual(g["grounded"], 1)
        self.assertTrue(g["export_ready"])


if __name__ == "__main__":
    unittest.main()
