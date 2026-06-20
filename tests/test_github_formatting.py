"""
Tests for GitHub-to-IEEE output cleaning (formatting fix).
"""

import unittest

from backend.core_agents.github_paper_agent import GitHubPaperAgent


class CleanTextTest(unittest.TestCase):
    def test_strips_preamble_and_header(self):
        raw = "Sure, here is the abstract:\n\n## Abstract\nThis system works well."
        out = GitHubPaperAgent._clean_text(raw, "Abstract")
        self.assertEqual(out, "This system works well.")

    def test_strips_markdown_emphasis_and_code(self):
        raw = "This **system** uses a `scalable` and *novel* approach."
        out = GitHubPaperAgent._clean_text(raw)
        self.assertEqual(out, "This system uses a scalable and novel approach.")

    def test_strips_code_fences(self):
        raw = "```\nThe project addresses scaling.\n```"
        out = GitHubPaperAgent._clean_text(raw, "Introduction")
        self.assertEqual(out, "The project addresses scaling.")

    def test_preserves_paragraph_breaks(self):
        raw = "First paragraph.\n\nSecond paragraph."
        out = GitHubPaperAgent._clean_text(raw)
        self.assertIn("\n\n", out)

    def test_strips_wrapping_quotes_for_title(self):
        out = GitHubPaperAgent._clean_text('"A Novel **Approach**"')
        self.assertEqual(out, "A Novel Approach")

    def test_empty(self):
        self.assertEqual(GitHubPaperAgent._clean_text(""), "")


if __name__ == "__main__":
    unittest.main()
