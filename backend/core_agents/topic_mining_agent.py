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
    def __init__(
        self,
        use_semantic: bool = True,
        max_clusters: int = 6,
        use_slm: bool = True,
        method: str = "auto",
    ):
        self.use_semantic = use_semantic
        self.max_clusters = max_clusters
        self.use_slm = use_slm          # SLM 3-attribute extraction before embedding
        self.method = method            # "auto" | "kmeans" | "hdbscan"

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

    def _extract_attributes(self, papers: List[Dict[str, Any]]):
        """SLM pass: extract {core_methodology, primary_problem_domain,
        key_contribution} per abstract. Returns a list of PaperAttributes, or
        None if no LLM produced anything (caller falls back to raw text)."""
        try:
            from concurrent.futures import ThreadPoolExecutor
            from backend.runtime.models import small_model
            from backend.core_agents.schemas import PaperAttributes
            from backend.core_agents.query_builder import _safe_json
        except Exception:  # pragma: no cover
            return None

        prompt_tmpl = (
            "You are a scientific abstract analyzer. Bypass syntactic noise and extract "
            "EXACTLY three attributes. Output ONLY a JSON object, no prose.\n\n"
            "Abstract:\n\"\"\"{text}\"\"\"\n\n"
            "Return JSON with EXACTLY these keys (each a concise phrase <= 12 words):\n"
            '{{"core_methodology": "...", "primary_problem_domain": "...", "key_contribution": "..."}}'
        )

        def _one(p: Dict[str, Any]):
            text = (p.get("abstract") or p.get("title") or "").strip()[:1500]
            if not text:
                return PaperAttributes()
            try:
                raw = small_model(prompt_tmpl.format(text=text), max_tokens=200, temperature=0.1)
                data = _safe_json(raw) or {}
                return PaperAttributes(
                    core_methodology=str(data.get("core_methodology", "")).strip(),
                    primary_problem_domain=str(data.get("primary_problem_domain", "")).strip(),
                    key_contribution=str(data.get("key_contribution", "")).strip(),
                )
            except Exception:  # noqa: BLE001
                return PaperAttributes()

        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(_one, papers))
        if all(not r.focused_text() for r in results):
            return None  # no LLM / all empty → signal fallback to raw text
        return results

    def _cluster_embeddings(self, embeddings, n: int):
        """Cluster embeddings → (labels, centroids|None, method). HDBSCAN when
        requested/available (auto for large corpora), else K-Means."""
        use_hdbscan = self.method == "hdbscan" or (self.method == "auto" and n >= 25)
        if use_hdbscan:
            try:
                import hdbscan
                labels = hdbscan.HDBSCAN(min_cluster_size=max(2, n // 10)).fit_predict(embeddings)
                if len({int(l) for l in labels if int(l) >= 0}) >= 2:
                    return labels, None, "hdbscan"
            except Exception as exc:  # noqa: BLE001
                print(f"   [!] HDBSCAN unavailable/failed ({exc}); using KMeans")
        try:
            from sklearn.cluster import KMeans
            k = max(2, min(self.max_clusters, n // 2))
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(embeddings)
            return labels, km.cluster_centers_, "kmeans"
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] KMeans failed: {exc}")
            return None, None, "none"

    def _cluster_semantic(self, papers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        model = _get_embed_model()
        if model is None:
            return None
        try:
            import numpy as np
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Topic mining clustering unavailable: {exc}")
            return None

        # SLM 3-attribute extraction → focused embedding text (fallback: title+abstract).
        attributes = self._extract_attributes(papers) if self.use_slm else None
        docs: List[str] = []
        for i, p in enumerate(papers):
            focused = attributes[i].focused_text() if (attributes and i < len(attributes)) else ""
            docs.append((focused or f"{p.get('title', '')}. {p.get('abstract', '')}")[:512])

        try:
            embeddings = model.encode(docs, convert_to_numpy=True, normalize_embeddings=True)
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Topic mining embedding failed: {exc}")
            return None

        n = len(papers)
        labels, centroids, method = self._cluster_embeddings(embeddings, n)
        if labels is None:
            return None

        clusters: List[Dict[str, Any]] = []
        for cid in sorted({int(l) for l in labels if int(l) >= 0}):
            members = [i for i, lab in enumerate(labels) if int(lab) == cid]
            if not members:
                continue
            cluster_papers = [papers[i] for i in members]
            cent = (
                centroids[cid]
                if centroids is not None and cid < len(centroids)
                else np.mean(embeddings[members], axis=0)
            )
            dists = [float(np.linalg.norm(embeddings[i] - cent)) for i in members]
            rep_idx = members[int(np.argmin(dists))]
            theme, keywords = self._label_cluster(cluster_papers)
            clusters.append({
                "id": cid,
                "theme": theme,
                "keywords": keywords,
                "size": len(members),
                "representative": papers[rep_idx].get("title", ""),
                "papers": [p.get("title", "") for p in cluster_papers],
                "centroid": cent.tolist(),
            })

        clusters.sort(key=lambda c: c["size"], reverse=True)

        # Silhouette score (exclude HDBSCAN noise label -1).
        silhouette = None
        try:
            from sklearn.metrics import silhouette_score
            valid = [i for i, l in enumerate(labels) if int(l) >= 0]
            vlabels = [int(labels[i]) for i in valid]
            if 2 <= len(set(vlabels)) < len(valid):
                silhouette = round(float(silhouette_score(embeddings[valid], vlabels)), 4)
        except Exception:  # noqa: BLE001
            silhouette = None

        metrics = {
            "method": method,
            "n_clusters": len(clusters),
            "silhouette": silhouette,
            "n_papers": n,
            "attributes_extracted": bool(attributes),
        }
        return {"clusters": clusters, "method": method, "metrics": metrics, "_stub": False}

    def mine_models(self, papers, query_analysis=None):
        """Typed accessor: return the mining result as a Pydantic model."""
        from backend.core_agents.schemas import TopicMiningResult
        return TopicMiningResult.from_result(self.mine(papers, query_analysis))

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
            "metrics": {
                "method": "subtopic_fallback",
                "n_clusters": len(clusters),
                "silhouette": None,
                "n_papers": len(papers),
                "attributes_extracted": False,
            },
            "_stub": False,
        }
