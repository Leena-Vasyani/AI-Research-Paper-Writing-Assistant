"""
Phase 1 tests for the Search Agent + Citation Graph.

Offline: CrossRef HTTP is mocked; semantic features disabled so no model loads.
"""

import unittest
from unittest.mock import MagicMock

from backend.core_agents.search_agent import SearchAgent, PaperRetrievalAgent
from backend.core_agents.knowledge.citation_graph import CitationGraph


_CROSSREF_PAYLOAD = {
    "message": {
        "items": [
            {
                "DOI": "10.1000/aaa",
                "title": ["Graph Neural Networks for Smart Grids"],
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "abstract": "<jats:p>We study <b>GNNs</b> for grids.</jats:p>",
                "issued": {"date-parts": [[2023, 5]]},
                "container-title": ["IEEE TPS"],
                "is-referenced-by-count": 42,
                "URL": "https://doi.org/10.1000/aaa",
                "reference": [{"DOI": "10.1000/bbb"}, {"key": "no-doi"}],
            },
            {"title": [""]},  # malformed → skipped
        ]
    }
}


class CitationGraphTest(unittest.TestCase):
    def test_reference_and_related_edges(self):
        papers = [
            {"title": "A deep model", "doi": "10/a", "citations": 9,
             "published": "2022", "references": [{"DOI": "10/b"}]},
            {"title": "A deep model variant", "doi": "10/b", "citations": 3,
             "published": "2021"},
        ]
        g = CitationGraph.from_papers(papers).to_dict()
        self.assertEqual(g["stats"]["node_count"], 2)
        self.assertGreaterEqual(g["stats"]["reference_edges"], 1)
        ref_edges = [e for e in g["edges"] if e["kind"] == "references"]
        self.assertEqual(ref_edges[0]["source"], "doi:10/a")
        self.assertEqual(ref_edges[0]["target"], "doi:10/b")

    def test_empty_papers(self):
        g = CitationGraph.from_papers([]).to_dict()
        self.assertEqual(g["stats"]["node_count"], 0)
        self.assertEqual(g["stats"]["edge_count"], 0)


class SearchAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = SearchAgent(use_semantic=False)

    def test_backcompat_alias(self):
        self.assertIs(PaperRetrievalAgent, SearchAgent)

    def test_crossref_parsing_and_references(self):
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = _CROSSREF_PAYLOAD
        self.agent._session = MagicMock()
        self.agent._session.get.return_value = fake_resp

        papers = self.agent._retrieve_crossref(["smart grid", "gnn"], max_results=5)
        self.assertEqual(len(papers), 1)  # malformed item dropped
        p = papers[0]
        self.assertEqual(p["source"], "crossref")
        self.assertEqual(p["doi"], "10.1000/aaa")
        self.assertEqual(p["citations"], 42)
        self.assertNotIn("<", p["abstract"])  # JATS tags stripped
        self.assertEqual(p["references"], [{"DOI": "10.1000/bbb"}])  # only DOI refs kept

    def test_crossref_to_citation_graph_wires_references(self):
        # Two crossref papers where one references the other → directed edge.
        papers = [
            {"title": "Paper A", "doi": "10.1000/aaa", "source": "crossref",
             "published": "2023", "citations": 5, "references": [{"DOI": "10.1000/bbb"}]},
            {"title": "Paper B", "doi": "10.1000/bbb", "source": "crossref",
             "published": "2022", "citations": 1},
        ]
        graph = self.agent.build_citation_graph(papers)
        self.assertEqual(graph["stats"]["reference_edges"], 1)


if __name__ == "__main__":
    unittest.main()
