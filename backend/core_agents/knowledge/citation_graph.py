"""
Citation Graph — the shared "domain-explicit knowledge" source from the
architecture diagrams.

Built once by the Search Agent from retrieved paper metadata and consumed
downstream by the Outline Agent (structure/lit-review planning) and the Review
Agent (grounding / contradiction checks).

The graph is intentionally lightweight and dependency-free:
  - nodes: one per retrieved paper, keyed by a stable id (DOI > entry_id > url > title)
  - edges:
      * "references" — when a paper's CrossRef reference list cites another node
        (directed: citing -> cited)
      * "related"    — heuristic undirected links from shared venue / authors /
        keyword overlap, so the graph is still useful when reference lists are
        absent (arXiv/PubMed rarely expose them)

``to_dict()`` returns a JSON-serializable structure that drops straight into
``PipelineState['citation_graph']``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

_WORD_RE = re.compile(r"[a-z0-9]+")


def _norm_doi(doi: Optional[str]) -> str:
    doi = (doi or "").strip().lower()
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return doi


def _paper_id(paper: Dict[str, Any]) -> str:
    """Stable identity for a paper: DOI > entry_id > url > normalized title."""
    doi = _norm_doi(paper.get("doi"))
    if doi:
        return f"doi:{doi}"
    for key in ("entry_id", "url"):
        val = (paper.get(key) or "").strip()
        if val:
            return val
    return "title:" + (paper.get("title") or "").strip().lower()


def _year_of(paper: Dict[str, Any]) -> Optional[int]:
    raw = str(paper.get("published") or paper.get("year") or "")
    m = re.search(r"\d{4}", raw)
    return int(m.group()) if m else None


def _keywords(paper: Dict[str, Any]) -> Set[str]:
    text = f"{paper.get('title', '')} {paper.get('primary_category', '')}".lower()
    return {w for w in _WORD_RE.findall(text) if len(w) > 3}


class CitationGraph:
    """A small directed/undirected hybrid graph over retrieved papers."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        # edges: (src_id, dst_id, kind, weight)
        self.edges: List[Tuple[str, str, str, float]] = []

    # -- construction -------------------------------------------------------

    @classmethod
    def from_papers(cls, papers: List[Dict[str, Any]]) -> "CitationGraph":
        graph = cls()
        for paper in papers or []:
            graph._add_node(paper)
        graph._add_reference_edges(papers or [])
        graph._add_related_edges()
        return graph

    def _add_node(self, paper: Dict[str, Any]) -> str:
        node_id = _paper_id(paper)
        if node_id not in self.nodes:
            self.nodes[node_id] = {
                "id": node_id,
                "title": paper.get("title", ""),
                "year": _year_of(paper),
                "citations": int(paper.get("citations", 0) or 0),
                "source": paper.get("source", ""),
                "doi": _norm_doi(paper.get("doi")),
                "url": paper.get("url", ""),
                "venue": paper.get("primary_category", ""),
            }
        return node_id

    def _add_reference_edges(self, papers: List[Dict[str, Any]]) -> None:
        """Directed citing -> cited edges from CrossRef reference DOIs."""
        doi_index = {n["doi"]: nid for nid, n in self.nodes.items() if n.get("doi")}
        for paper in papers:
            src = _paper_id(paper)
            for ref in paper.get("references", []) or []:
                ref_doi = _norm_doi(ref.get("DOI") if isinstance(ref, dict) else ref)
                if ref_doi and ref_doi in doi_index:
                    dst = doi_index[ref_doi]
                    if dst != src:
                        self.edges.append((src, dst, "references", 1.0))

    def _add_related_edges(self) -> None:
        """Undirected heuristic links so the graph isn't empty without refs."""
        node_kw = {nid: _keywords(n) for nid, n in self.nodes.items()}
        ids = list(self.nodes.keys())
        seen: Set[frozenset] = set()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                pair = frozenset((a, b))
                if pair in seen:
                    continue
                ka, kb = node_kw[a], node_kw[b]
                if not ka or not kb:
                    continue
                overlap = len(ka & kb) / max(1, len(ka | kb))
                if overlap >= 0.25:
                    self.edges.append((a, b, "related", round(overlap, 3)))
                    seen.add(pair)

    # -- queries / export ---------------------------------------------------

    def neighbors(self, node_id: str) -> List[str]:
        out: List[str] = []
        for src, dst, _kind, _w in self.edges:
            if src == node_id:
                out.append(dst)
            elif dst == node_id:
                out.append(src)
        return out

    def most_cited(self, top_n: int = 5) -> List[Dict[str, Any]]:
        return sorted(self.nodes.values(), key=lambda n: n.get("citations", 0), reverse=True)[:top_n]

    def to_dict(self) -> Dict[str, Any]:
        ref_edges = sum(1 for *_x, kind, _w in self.edges if kind == "references")
        return {
            "nodes": list(self.nodes.values()),
            "edges": [
                {"source": s, "target": t, "kind": k, "weight": w}
                for s, t, k, w in self.edges
            ],
            "stats": {
                "node_count": len(self.nodes),
                "edge_count": len(self.edges),
                "reference_edges": ref_edges,
                "related_edges": len(self.edges) - ref_edges,
            },
        }
