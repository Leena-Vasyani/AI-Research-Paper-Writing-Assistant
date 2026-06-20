"""
Phase 5 tests for the multi-critic Review Agent.

Offline: use_llm=False (heuristic critics) and use_plagiarism=False (no model
load); plagiarism is exercised by injecting a report.
"""

import unittest

from backend.core_agents.review_agent import ReviewAgent


class ReviewAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = ReviewAgent(use_llm=False, use_plagiarism=False, review_threshold=7.0)

    def test_review_structure(self):
        draft = {"sections": {
            "Introduction": "We study graph neural networks for smart grids. " * 5,
            "Methodology": "We describe the proposed approach in detail. " * 5,
            "Results": "Prior work [1] reported similar findings. " * 5,
        }}
        r = self.agent.review(draft, topic="GNNs for grids")
        for axis in ["novelty", "coherence", "evidence_quality", "writing_reproducibility", "originality"]:
            self.assertIn(axis, r["scores"])
            self.assertTrue(0.0 <= r["scores"][axis] <= 10.0)
        self.assertIn("mean_score", r)
        self.assertIn("has_critical_issues", r)
        self.assertIn(r["recommendation"], {"accept", "weak_accept", "revise", "reject"})
        self.assertEqual(r["method"], "heuristic")

    def test_unsupported_claim_high_severity(self):
        draft = {"sections": {
            "Results": "Our method achieves 95% accuracy and outperforms all baselines "
                       "by a wide margin across every benchmark we evaluated."
        }}
        r = self.agent.review(draft, topic="t")
        claims = r["unsupported_claims"]
        self.assertTrue(claims)
        self.assertTrue(any(c["severity"] == "H" for c in claims))
        # critique surfaces it under the section
        self.assertIn("Results", r["critique"])

    def test_grounded_claim_not_flagged(self):
        draft = {"sections": {
            "Results": "Our method achieves strong accuracy and outperforms baselines [1]."
        }}
        r = self.agent.review(draft, topic="t")
        self.assertEqual(r["unsupported_claims"], [])

    def test_originality_from_plagiarism_report(self):
        self.assertEqual(self.agent._originality_score({"overall_score": 0.9}), 1.0)
        self.assertEqual(self.agent._originality_score({}), 7.0)

    def test_plagiarism_high_is_critical(self):
        draft = {"sections": {"Introduction": "Some text here for the section body."}}
        r = self.agent.review(
            draft, topic="t",
            plagiarism_report={"overall_score": 0.8, "overall_status": "high"},
        )
        self.assertTrue(r["has_critical_issues"])
        self.assertEqual(r["scores"]["originality"], 2.0)

    def test_recommendation_mapping(self):
        self.assertEqual(self.agent._recommend(8.5, False), "accept")
        self.assertEqual(self.agent._recommend(7.0, False), "weak_accept")
        self.assertEqual(self.agent._recommend(5.0, False), "revise")
        self.assertEqual(self.agent._recommend(4.0, True), "reject")
        self.assertEqual(self.agent._recommend(6.0, True), "revise")


if __name__ == "__main__":
    unittest.main()
