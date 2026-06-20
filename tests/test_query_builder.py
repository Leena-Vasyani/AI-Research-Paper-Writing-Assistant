"""
Tests for the boolean query builder (Track B + consolidation).
"""

import unittest

import backend.core_agents.query_builder as qb
from backend.core_agents.query_builder import (
    ExpansionResult,
    build_boolean_queries,
    strip_boolean,
)


class BuildBooleanQueriesTest(unittest.TestCase):
    def test_generates_boolean_strings(self):
        kws = ["graph neural network", "load forecasting", "smart grid"]
        track_a = {
            "graph neural network": ["gnn"],
            "load forecasting": ["demand prediction"],
            "smart grid": ["power grid"],
        }
        qs = build_boolean_queries(kws, track_a, ExpansionResult(jargon=["spatio-temporal gnn"]), target=28)
        self.assertTrue(qs)
        self.assertLessEqual(len(qs), 28)
        joined = " ".join(qs)
        self.assertIn(" AND ", joined)
        self.assertIn(" OR ", joined)  # OR-groups from synonyms
        # no duplicate queries
        self.assertEqual(len(qs), len({q.lower() for q in qs}))

    def test_phrases_are_quoted(self):
        qs = build_boolean_queries(["machine learning"], {"machine learning": ["ml"]})
        self.assertTrue(any('"machine learning"' in q for q in qs))

    def test_exclusions_use_andnot(self):
        qs = build_boolean_queries(["robotics"], {}, exclusions=["survey"])
        self.assertTrue(any("ANDNOT" in q for q in qs))

    def test_empty_keywords(self):
        self.assertEqual(build_boolean_queries([], {}), [])

    def test_target_cap(self):
        kws = [f"kw{i}" for i in range(8)]
        qs = build_boolean_queries(kws, {}, target=25)
        self.assertLessEqual(len(qs), 25)
        self.assertGreaterEqual(len(qs), 20)  # 8 singles + 28 pairs → capped at 25


class StripBooleanTest(unittest.TestCase):
    def test_removes_operators(self):
        s = strip_boolean('("graph neural network" OR gnn) AND "smart grid" ANDNOT survey')
        self.assertNotIn("AND", s)
        self.assertNotIn("OR", s)
        self.assertIn("graph neural network", s)
        self.assertIn("smart grid", s)


class LlmExpandTest(unittest.TestCase):
    def test_parses_into_model(self):
        orig = qb.chat_completion
        qb.chat_completion = lambda *a, **k: (
            '{"jargon":["spatio-temporal"],"acronyms":["GNN = graph neural network"],'
            '"boolean_clauses":["(\\"a\\" OR \\"b\\")"]}'
        )
        try:
            r = qb.llm_expand("topic", ["kw"])
            self.assertIsInstance(r, ExpansionResult)
            self.assertEqual(r.jargon, ["spatio-temporal"])
            self.assertTrue(r.boolean_clauses)
        finally:
            qb.chat_completion = orig

    def test_no_llm_returns_empty(self):
        orig = qb.chat_completion
        qb.chat_completion = None
        try:
            r = qb.llm_expand("topic", ["kw"])
            self.assertEqual(r.jargon, [])
        finally:
            qb.chat_completion = orig


if __name__ == "__main__":
    unittest.main()
