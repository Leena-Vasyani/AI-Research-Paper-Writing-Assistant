"""
Graph-level tests for the LangGraph runtime (Phase 0).

These run fully offline: the heavy agents are replaced with fakes so we verify
the orchestration (stage ordering, revision loop, termination) rather than
agent quality.
"""

import unittest

from backend.runtime.graph import build_pipeline_graph, _after_review
from backend.runtime.state import new_state
import backend.runtime.nodes.search as search_mod
import backend.runtime.nodes.drafting as drafting_mod
import backend.runtime.nodes.review as review_mod
import backend.runtime.nodes.citation as citation_mod


# --- Fakes -----------------------------------------------------------------

class _FakeQueryAgent:
    def run(self, text, top_keywords=8):
        return {
            "keywords": ["alpha", "beta"],
            "subtopics": {"theme-1": ["alpha"], "theme-2": ["beta"]},
            "search_strategy": {"max_results": 3},
        }


class _FakeSearchAgent:
    def retrieve_papers_multi_query(self, keywords, subtopics, max_results=5):
        return {"papers": [{"title": "P1", "abstract": "a"}], "warnings": [],
                "citation_graph": {"nodes": [], "edges": [], "stats": {}}}

    def retrieve_papers(self, keywords, max_results=5):
        return {"papers": [{"title": "P1", "abstract": "a"}], "warnings": [],
                "citation_graph": {"nodes": [], "edges": [], "stats": {}}}


class _FakeSummarizer:
    def generate_comprehensive_summary(self, papers, keywords):
        return {"executive_summary": "summary", "section_summaries": {}}


class _FakeDrafter:
    def generate_complete_draft(self, topic, summary, keywords):
        return {"abstract": "abs", "introduction": "intro", "related_work": "rw"}


class _FakePlagiarismCritical:
    """Always reports critical overlap -> forces the revision loop."""
    def check_plagiarism(self, sections, papers, topic):
        return {"overall_score": 0.9, "overall_status": "high", "section_analyses": []}


class _FakeCitation:
    def add_citations_to_draft(self, sections, papers, plagiarism_results=None, citation_style="ieee"):
        return {"cited_draft": sections, "references": ["[1] ref"]}


class RuntimeGraphTest(unittest.TestCase):
    def setUp(self):
        # Patch the agent symbols bound inside each node module.
        self._patches = [
            (search_mod, "query_agent", lambda: _FakeQueryAgent()),
            (search_mod, "search_agent", lambda: _FakeSearchAgent()),
            (drafting_mod, "summarization_agent", lambda: _FakeSummarizer()),
            (drafting_mod, "drafting_agent", lambda: _FakeDrafter()),
            (review_mod, "plagiarism_agent", lambda: _FakePlagiarismCritical()),
            (citation_mod, "citation_agent", lambda: _FakeCitation()),
        ]
        self._originals = [(mod, name, getattr(mod, name)) for mod, name, _ in self._patches]
        for mod, name, fake in self._patches:
            setattr(mod, name, fake)

    def tearDown(self):
        for mod, name, original in self._originals:
            setattr(mod, name, original)

    def test_after_review_conditional(self):
        # passing score, no critical issues -> proceed
        s = new_state("t")
        s["review"] = {"mean_score": 9.0, "has_critical_issues": False}
        s["revision_count"] = 0
        self.assertEqual(_after_review(s), "proceed")
        # failing score, budget remaining -> revise
        s["review"] = {"mean_score": 2.0, "has_critical_issues": True}
        self.assertEqual(_after_review(s), "revise")
        # failing score, budget exhausted -> proceed
        s["revision_count"] = 2
        s["max_revisions"] = 2
        self.assertEqual(_after_review(s), "proceed")

    def test_pipeline_runs_and_loop_terminates(self):
        graph = build_pipeline_graph()
        state = new_state("test topic", max_revisions=2)
        result = graph.invoke(state, config={"recursion_limit": 50})

        # Reached the end with a final document.
        self.assertEqual(result.get("status"), "completed")
        self.assertIn("final_document", result)
        self.assertTrue(result["final_document"].get("sections"))

        # All upstream stages populated.
        self.assertTrue(result.get("corpus"))
        self.assertTrue(result.get("themes"))
        self.assertTrue(result.get("blueprint"))
        self.assertTrue(result.get("draft", {}).get("sections"))
        self.assertIn("review", result)

        # Critical plagiarism forces the loop to exhaust its budget, then proceed.
        self.assertEqual(result.get("revision_count"), 2)
        # Timings recorded for each stage.
        self.assertIn("formatter", result.get("stage_timings", {}))


if __name__ == "__main__":
    unittest.main()
