"""
Tests for Track-A thesaurus expansion (domain thesaurus path; WordNet forced
off for determinism/offline).
"""

import unittest

import backend.core_agents.knowledge.thesaurus as th
from backend.core_agents.knowledge.thesaurus import expand_terms


class ThesaurusTest(unittest.TestCase):
    def setUp(self):
        self._orig = th._WORDNET
        th._WORDNET = False  # force domain-thesaurus-only, no nltk/download

    def tearDown(self):
        th._WORDNET = self._orig

    def test_acronym_to_expansion(self):
        r = expand_terms(["cnn"])
        self.assertIn("convolutional neural network", r["cnn"])

    def test_expansion_to_acronym(self):
        r = expand_terms(["convolutional neural network"])
        self.assertIn("cnn", r["convolutional neural network"])

    def test_unknown_term_is_graceful(self):
        r = expand_terms(["zzzql"])
        self.assertIsInstance(r.get("zzzql"), list)  # empty list, no error

    def test_empty(self):
        self.assertEqual(expand_terms([]), {})


if __name__ == "__main__":
    unittest.main()
