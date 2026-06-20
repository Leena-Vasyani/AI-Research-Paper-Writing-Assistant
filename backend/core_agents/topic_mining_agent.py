"""
Topic Mining Agent.

Clusters the retrieved corpus into themes / a lightweight taxonomy and surfaces
coverage gaps — the "Topic Mining" / "Clustering" stage from the PDR (§7) and
architecture diagrams. Its output feeds the Outline Agent's structure planning.

Approach (all graceful-degrading):
  1. Embed each paper (title + abstract) with the shared SentenceTransformer
     (``all-MiniLM-L6-v2``, reused from the Search Agent so only one copy loads).
  2. Cluster embeddings with KMeans (k chosen by a simple size heuristic).
  3. Label each cluster with top TF-IDF terms; pick a centroid-nearest
     representative paper.
  4. Derive coverage gaps from the query analysis (subtopics poorly covered by
     any cluster + any explicit research gaps).

If embeddings or scikit-learn are unavailable, falls back to grouping by the
query analysis subtopics so downstream stages always receive usable themes.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Dict, List, Optional

# Reuse the Search Agent's lazily-cached embedding model (single instance).
try:
    from backend.core_agents.search_agent import _get_embed_model
except Exception:  # pragma: no cover - import guard
    _get_embed_model = lambda: None  # type: ignore[assignment]

_GAP_SIM_THRESHOLD = float(os.getenv("TOPIC_GAP_SIM_THRESHOLD", "0.35"))


class TopicMiningAgent:
    def __init__(self, use_semantic: bool = True, max_clusters: int = 6):
        self.use_semantic = use_semantic
        self.max_clusters = max_clusters

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mine(
        self,
        papers: List[Dict[str, Any]],
        query_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        query_analysis = query_analysis or {}
        papers = papers or []

        if self.use_semantic and len(papers) >= 4:
            result = self._cluster_semantic(papers)
            if result is not None:
                result["gaps"] = self._coverage_gaps(result["clusters"], query_analysis)
                result["taxonomy"] = [c["theme"] for c in result["clusters"]]
                return result

        # Fallback: group by query subtopics (no embeddings needed).
        return self._fallback(papers, query_analysis)

    # ------------------------------------------------------------------
    # Semantic clustering
    # ------------------------------------------------------------------

    def _cluster_semantic(self, papers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        model = _get_embed_model()
        if model is None:
            return None
        try:
            import numpy as np
            from sklearn.cluster import KMeans
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Topic mining clustering unavailable: {exc}")
            return None

        docs = [f"{p.get('title', '')}. {p.get('abstract', '')}"[:512] for p in papers]
        try:
            embeddings = model.encode(docs, convert_to_numpy=True, normalize_embeddings=True)
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Topic mining embedding failed: {exc}")
            return None

        n = len(papers)
        k = max(2, min(self.max_clusters, n // 2))
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(embeddings)
            centroids = km.cluster_centers_
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] KMeans failed: {exc}")
            return None

        clusters: List[Dict[str, Any]] = []
        for cid in range(k):
            members = [i for i, lab in enumerate(labels) if lab == cid]
            if not members:
                continue
            cluster_papers = [papers[i] for i in members]
            # representative = paper nearest the centroid
            import numpy as np
            dists = [float(np.linalg.norm(embeddings[i] - centroids[cid])) for i in members]
            rep_idx = members[int(np.argmin(dists))]
            theme, keywords = self._label_cluster(cluster_papers)
            clusters.append({
                "id": cid,
                "theme": theme,
                "keywords": keywords,
                "size": len(members),
                "representative": papers[rep_idx].get("title", ""),
                "papers": [p.get("title", "") for p in cluster_papers],
                "centroid": centroids[cid].tolist(),
            })

        clusters.sort(key=lambda c: c["size"], reverse=True)
        return {"clusters": clusters, "method": "kmeans", "_stub": False}

    def _label_cluster(self, cluster_papers: List[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Top TF-IDF terms across the cluster's titles/abstracts as a label."""
        docs = [f"{p.get('title', '')}. {p.get('abstract', '')}" for p in cluster_papers]
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(
                stop_words="english", ngram_range=(1, 2), max_features=400
            )
            matrix = vec.fit_transform(docs)
            scores = matrix.sum(axis=0).A1
            terms = vec.get_feature_names_out()
            ranked = [terms[i] for i in scores.argsort()[::-1][:6]]
            keywords = ranked[:5]
            theme = ", ".join(ranked[:3]).title() if ranked else "Theme"
            return theme, keywords
        except Exception:
            # Fallback: most common title words
            words = Counter()
            for p in cluster_papers:
                for w in (p.get("title", "") or "").lower().split():
                    if len(w) > 4:
                        words[w] += 1
            common = [w for w, _ in words.most_common(5)]
            return (", ".join(common[:3]).title() or "Theme"), common

    # ------------------------------------------------------------------
    # Coverage gaps
    # ------------------------------------------------------------------

    def _coverage_gaps(
        self, clusters: List[Dict[str, Any]], query_analysis: Dict[str, Any]
    ) -> List[str]:
        gaps: List[str] = list(query_analysis.get("research_gaps", []) or [])

        subtopics = query_analysis.get("subtopics", {}) or {}
        model = _get_embed_model()
        centroids = [c.get("centroid") for c in clusters if c.get("centroid")]
        if model is not None and centroids and subtopics:
            try:
                import numpy as np
                cent = np.array(centroids)
                names = list(subtopics.keys())
                emb = model.encode(names, convert_to_numpy=True, normalize_embeddings=True)
                # cosine sim = dot (vectors already normalized)
                sims = emb @ cent.T
                for name, row in zip(names, sims):
                    if float(row.max()) < _GAP_SIM_THRESHOLD:
                        gaps.append(f"Underexplored subtopic: {name}")
            except Exception:
                pass

        # Singleton clusters are niche/thinly covered themes.
        for c in clusters:
            if c["size"] == 1:
                gaps.append(f"Thinly covered theme: {c['theme']}")

        # de-dup preserving order
        seen: set = set()
        out: List[str] = []
        for g in gaps:
            if g not in seen:
                seen.add(g)
                out.append(g)
        return out

    # ------------------------------------------------------------------
    # Fallback (no embeddings / small corpus)
    # ------------------------------------------------------------------

    def _fallback(
        self, papers: List[Dict[str, Any]], query_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        subtopics = query_analysis.get("subtopics", {}) or {}
        clusters = [
            {
                "id": i,
                "theme": name,
                "keywords": kws,
                "size": len(papers),
                "representative": papers[0].get("title", "") if papers else "",
                "papers": [p.get("title", "") for p in papers],
            }
            for i, (name, kws) in enumerate(subtopics.items())
        ]
        if not clusters:
            clusters = [{
                "id": 0,
                "theme": query_analysis.get("original_topic", "General"),
                "keywords": query_analysis.get("keywords", []),
                "size": len(papers),
                "representative": papers[0].get("title", "") if papers else "",
                "papers": [p.get("title", "") for p in papers],
            }]
        return {
            "clusters": clusters,
            "taxonomy": [c["theme"] for c in clusters],
            "gaps": list(query_analysis.get("research_gaps", []) or []),
            "method": "subtopic_fallback",
            "_stub": False,
        }
