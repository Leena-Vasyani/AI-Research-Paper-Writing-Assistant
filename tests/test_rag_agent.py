"""
Tests for RAG/DocChat improvements: PDF text cleaning + follow-up
contextualization. (Persistence round-trip is exercised separately as an
integration check since it loads the embedding model.)
"""

import unittest

from backend.core_agents.rag_agent import RAGAgent


class PdfCleanTest(unittest.TestCase):
    def test_dehyphenation_and_softwrap(self):
        raw = "This sentence wraps\nacross lines with optimi-\nzation."
        out = RAGAgent._clean_pdf_text(raw)
        self.assertIn("optimization", out)
        self.assertIn("wraps across lines", out)

    def test_paragraph_breaks_preserved(self):
        raw = "Para one line one.\n\nPara two."
        out = RAGAgent._clean_pdf_text(raw)
        self.assertEqual(out.count("\n\n"), 1)


class ContextualizeQueryTest(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"role": "user", "content": "What is the proposed GNN architecture?"},
            {"role": "assistant", "content": "It is a spatio-temporal GNN."},
        ]

    def test_followup_pronoun_expanded(self):
        q = RAGAgent._contextualize_query("What about its limitations?", self.history)
        self.assertIn("GNN architecture", q)
        self.assertIn("limitations", q)

    def test_short_followup_expanded(self):
        q = RAGAgent._contextualize_query("And the dataset?", self.history)
        self.assertIn("GNN architecture", q)

    def test_standalone_question_unchanged(self):
        q = "What evaluation metrics were used to compare the baseline models?"
        self.assertEqual(RAGAgent._contextualize_query(q, self.history), q)

    def test_no_history(self):
        self.assertEqual(RAGAgent._contextualize_query("it?", []), "it?")


if __name__ == "__main__":
    unittest.main()
