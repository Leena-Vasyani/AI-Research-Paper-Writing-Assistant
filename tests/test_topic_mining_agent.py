"""
Phase 2 tests for the Topic Mining Agent.

The deterministic tests (fallback grouping, TF-IDF labeling, gap detection) run
offline with no model. A semantic-clustering test is included but skips
gracefully if the embedding model can't be loaded in this environment.
"""

import unittest

from backend.core_agents.topic_mining_agent import TopicMiningAgent


def _paper(title, abstract=""):
    return {"title": title, "abstract": abstract}


class TopicMiningFallbackTest(unittest.TestCase):
    def setUp(self):
        self.agent = TopicMiningAgent(use_semantic=False)

    def test_fallback_groups_by_subtopics(self):
        papers = [_paper("A"), _paper("B")]
        qa = {
            "subtopics": {"battery storage": ["lithium"], "solar forecasting": ["pv"]},
            "research_gaps": ["no long-horizon evaluation"],
        }
        result = self.agent.mine(papers, query_analysis=qa)
        self.assertEqual(result["method"], "subtopic_fallback")
        self.assertEqual(len(result["clusters"]), 2)
        self.assertEqual(result["taxonomy"], ["battery storage", "solar forecasting"])
        self.assertIn("no long-horizon evaluation", result["gaps"])

    def test_fallback_single_cluster_when_no_subtopics(self):
        result = self.agent.mine([_paper("X")], query_analysis={"original_topic": "Smart Grids"})
        self.assertEqual(len(result["clusters"]), 1)
        self.assertEqual(result["clusters"][0]["theme"], "Smart Grids")

    def test_label_cluster_tfidf(self):
        cluster = [
            _paper("Reinforcement learning for energy management",
                   "reinforcement learning controls home energy"),
            _paper("Deep reinforcement learning energy",
                   "reinforcement learning energy management policies"),
        ]
        theme, keywords = self.agent._label_cluster(cluster)
        self.assertTrue(theme)
        self.assertTrue(any("reinforcement" in k or "energy" in k for k in keywords))

    def test_coverage_gaps_flags_singletons(self):
        clusters = [
            {"theme": "Mainstream Topic", "size": 5, "centroid": None},
            {"theme": "Niche Topic", "size": 1, "centroid": None},
        ]
        gaps = self.agent._coverage_gaps(clusters, {})
        self.assertIn("Thinly covered theme: Niche Topic", gaps)


class TopicMiningSemanticTest(unittest.TestCase):
    def test_semantic_clustering_separates_topics(self):
        from backend.core_agents.search_agent import _get_embed_model
        if _get_embed_model() is None:
            self.skipTest("embedding model unavailable offline")

        # use_slm=False keeps it offline (no SLM attribute extraction call)
        agent = TopicMiningAgent(use_semantic=True, max_clusters=2, use_slm=False)
        papers = [
            _paper("Solar power forecasting with neural nets", "photovoltaic irradiance prediction"),
            _paper("Wind and solar generation forecasting", "renewable generation forecasting models"),
            _paper("Battery degradation modeling", "lithium-ion battery state of health"),
            _paper("Battery management systems", "battery cell balancing and degradation"),
        ]
        result = agent.mine(papers, query_analysis={})
        self.assertEqual(result["method"], "kmeans")
        self.assertGreaterEqual(len(result["clusters"]), 2)
        # every paper is assigned to some cluster
        total = sum(c["size"] for c in result["clusters"])
        self.assertEqual(total, len(papers))
        # metrics with a silhouette score are reported
        self.assertIn("metrics", result)
        self.assertIn("silhouette", result["metrics"])
        self.assertEqual(result["metrics"]["method"], "kmeans")


if __name__ == "__main__":
    unittest.main()
