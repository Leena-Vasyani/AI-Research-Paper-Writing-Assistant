"""
Dedicated Keyword Extraction Agent.

Hybrid approach:
  1. Fast path: LLM-based extraction for semantic understanding
  2. Reliable path: KeyBERT with all-MiniLM-L6-v2 as fallback
  3. Merge & deduplicate, enrich with confidence scores and type tags.
"""

from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional, Tuple

from backend.core_agents.cache import keyword_cache

try:
    from backend.core_agents.llm_provider import chat_completion
except Exception:
    chat_completion = None  # type: ignore[assignment]

try:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer
except Exception:
    KeyBERT = None  # type: ignore[misc,assignment]
    SentenceTransformer = None  # type: ignore[misc,assignment]

# Domain-aware stopwords — generic academic terms that dilute retrieval quality
_DOMAIN_STOPWORDS = {
    "paper", "study", "studies", "research", "article", "work", "works",
    "analysis", "analyses", "review", "survey", "approach", "method",
    "methods", "methodology", "technique", "techniques", "framework",
    "model", "models", "system", "systems", "algorithm", "algorithms",
    "application", "applications", "problem", "problems", "solution",
    "solutions", "result", "results", "finding", "findings", "contribution",
    "contributions", "limitation", "limitations", "future", "work",
    "proposal", "proposed", "using", "used", "use", "based", "based on",
    "via", "with", "without", "within", "among", "between", "over",
    "under", "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "also", "well", "new", "novel", "recent", "existing", "previous",
}

_LLM_KEYWORD_PROMPT = """You are a scientific keyword extraction engine.
Extract the most relevant technical keywords and key phrases from the following research query or text.

Rules:
- Focus on domain-specific terms, methods, entities, and concepts.
- Include multi-word phrases when they represent single concepts (e.g., "convolutional neural network").
- Expand any acronyms to their full form AND include the acronym itself.
- Exclude generic words like "paper", "study", "research", "method", "approach".
- Return ONLY a valid JSON object with this exact schema:
  {{"keywords": [{{"text": "...", "type": "core|method|domain|entity"}}, ...]}}
- Provide at most {top_n} keywords, ordered by relevance (most relevant first).
- Do not include markdown code blocks or explanations.

Text:
{text}
"""

_SYNONYM_PROMPT = """You are a scientific terminology assistant.
For each keyword below, suggest 2-4 scientific synonyms or alternative phrasings that could be used in academic literature.

Rules:
- Return ONLY a valid JSON object: {{"synonyms": {{"keyword1": ["alt1", "alt2"], ...}}}}
- Keep synonyms concise and academically relevant.
- Do not include markdown code blocks or explanations.

Keywords:
{keywords}
"""


class KeywordExtractionAgent:
    """
    Hybrid keyword extraction combining LLM semantic understanding
    with fast embedding-based fallback.
    """

    def __init__(self, use_llm: bool = True, use_embeddings: bool = True):
        self.use_llm = use_llm and chat_completion is not None
        self.use_embeddings = use_embeddings
        self._kw_model: Optional[object] = None
        self._embedding_model: Optional[object] = None
        self._init_embedding_model()

    def _init_embedding_model(self) -> None:
        if not self.use_embeddings:
            return
        if SentenceTransformer is None or KeyBERT is None:
            print("   [!] KeyBERT or SentenceTransformer not installed; embedding fallback disabled")
            self.use_embeddings = False
            return
        try:
            print("   [>>] Loading embedding model (all-MiniLM-L6-v2)...")
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            self._kw_model = KeyBERT(model=self._embedding_model)
            print("   [OK] Embedding model loaded")
        except Exception as exc:
            print(f"   [!] Embedding model load failed: {exc}")
            self.use_embeddings = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        text: str,
        top_n: int = 8,
        use_llm: Optional[bool] = None,
        expand_acronyms: bool = True,
        return_synonyms: bool = False,
    ) -> Dict:
        """
        Extract keywords from *text* using the hybrid pipeline.

        Returns:
            {
                "keywords": [{"text": str, "score": float, "type": str}, ...],
                "synonyms": {"keyword": ["alt1", ...], ...} | None,
                "provider": "llm" | "embedding" | "hybrid" | "fallback",
                "elapsed_ms": int,
            }
        """
        start = time.time()
        text = (text or "").strip()
        if not text:
            return self._empty_result(0)

        # Cache lookup
        cache_key = f"{hash(text)}:{top_n}:{expand_acronyms}:{return_synonyms}"
        cached = keyword_cache.get(cache_key)
        if cached is not None:
            cached["elapsed_ms"] = 0  # instant from cache
            return cached

        _use_llm = self.use_llm if use_llm is None else (use_llm and chat_completion is not None)

        llm_keywords: List[Dict] = []
        emb_keywords: List[Dict] = []

        # --- Path 1: LLM extraction ---
        if _use_llm:
            llm_keywords = self._extract_with_llm(text, top_n=top_n)

        # --- Path 2: Embedding extraction ---
        if self.use_embeddings:
            emb_keywords = self._extract_with_embeddings(text, top_n=top_n)

        # --- Merge & rank ---
        merged = self._merge_keywords(llm_keywords, emb_keywords, top_n=top_n)

        provider = "fallback"
        if _use_llm and self.use_embeddings:
            provider = "hybrid"
        elif _use_llm:
            provider = "llm"
        elif self.use_embeddings:
            provider = "embedding"

        # If both failed, fall back to simple token extraction
        if not merged:
            merged = self._fallback_token_extraction(text, top_n=top_n)
            provider = "fallback"

        # --- Post-processing ---
        merged = self._filter_stopwords(merged)
        merged = self._deduplicate_keywords(merged)

        # --- Acronym expansion ---
        if expand_acronyms:
            merged = self._expand_acronyms(text, merged)

        # --- Synonyms ---
        synonyms: Optional[Dict[str, List[str]]] = None
        if return_synonyms and _use_llm and chat_completion is not None:
            synonyms = self._generate_synonyms([k["text"] for k in merged[:top_n]])

        elapsed_ms = int((time.time() - start) * 1000)

        result = {
            "keywords": merged[:top_n],
            "synonyms": synonyms,
            "provider": provider,
            "elapsed_ms": elapsed_ms,
        }

        keyword_cache.set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_with_llm(self, text: str, top_n: int) -> List[Dict]:
        """Use LLM for semantic keyword extraction."""
        if chat_completion is None:
            return []
        prompt = _LLM_KEYWORD_PROMPT.format(text=text[:4000], top_n=top_n)
        try:
            raw = chat_completion(
                prompt,
                system="You extract scientific keywords. Respond ONLY with JSON.",
                max_tokens=600,
                temperature=0.1,
                top_p=0.9,
            )
            if not raw:
                return []
            data = self._safe_json_parse(raw)
            keywords = data.get("keywords", []) if isinstance(data, dict) else []
            results = []
            for item in keywords:
                if isinstance(item, dict) and "text" in item:
                    results.append({
                        "text": str(item["text"]).strip().lower(),
                        "score": float(item.get("score", 0.95)),
                        "type": str(item.get("type", "core")).strip().lower(),
                    })
            return results
        except Exception as exc:
            print(f"   [!] LLM keyword extraction failed: {exc}")
            return []

    def _extract_with_embeddings(self, text: str, top_n: int) -> List[Dict]:
        """Use KeyBERT for fast embedding-based keyword extraction."""
        if self._kw_model is None:
            return []
        try:
            keywords = self._kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words="english",
                top_n=top_n * 2,
                use_maxsum=True,
                nr_candidates=20,
                diversity=0.7,
            )
            results = []
            for kw, score in keywords:
                results.append({
                    "text": str(kw).strip().lower(),
                    "score": float(score),
                    "type": "core",
                })
            return results
        except Exception as exc:
            print(f"   [!] Embedding keyword extraction failed: {exc}")
            return []

    def _merge_keywords(
        self, llm_kws: List[Dict], emb_kws: List[Dict], top_n: int
    ) -> List[Dict]:
        """
        Merge LLM and embedding keywords.
        LLM keywords get a slight boost because they have semantic type tags.
        """
        merged_map: Dict[str, Dict] = {}

        for kw in llm_kws:
            txt = kw["text"]
            merged_map[txt] = {
                "text": txt,
                "score": kw.get("score", 0.95) * 1.05,  # slight LLM boost
                "type": kw.get("type", "core"),
            }

        for kw in emb_kws:
            txt = kw["text"]
            if txt in merged_map:
                # Average scores, keep LLM type tag if present
                merged_map[txt]["score"] = (
                    merged_map[txt]["score"] + kw.get("score", 0.5)
                ) / 2
            else:
                merged_map[txt] = {
                    "text": txt,
                    "score": kw.get("score", 0.5) * 0.95,
                    "type": kw.get("type", "core"),
                }

        sorted_kws = sorted(merged_map.values(), key=lambda x: x["score"], reverse=True)
        return sorted_kws[:top_n]

    def _filter_stopwords(self, keywords: List[Dict]) -> List[Dict]:
        """Remove generic academic stopwords."""
        filtered = []
        for kw in keywords:
            txt = kw["text"]
            # Drop exact matches and short generic tokens
            if txt in _DOMAIN_STOPWORDS:
                continue
            if len(txt) <= 2:
                continue
            # Penalize score slightly if it contains stopwords as substrings
            penalty = 0.0
            for sw in _DOMAIN_STOPWORDS:
                if len(sw) > 3 and sw in txt and sw != txt:
                    penalty += 0.02
            kw["score"] = max(0.0, kw["score"] - penalty)
            filtered.append(kw)
        return filtered

    def _deduplicate_keywords(self, keywords: List[Dict]) -> List[Dict]:
        """Remove near-duplicate keywords (e.g., 'deep learning' and 'deep learning model')."""
        if not keywords:
            return keywords
        deduped: List[Dict] = []
        seen_texts: List[str] = []
        for kw in keywords:
            txt = kw["text"]
            is_duplicate = False
            for seen in seen_texts:
                # If one is a substring of the other and lengths are close
                if txt in seen or seen in txt:
                    longer = seen if len(seen) > len(txt) else txt
                    shorter = txt if len(txt) < len(seen) else seen
                    # Only dedupe if the longer one isn't much longer (avoids false positives)
                    if len(longer) - len(shorter) <= 8:
                        is_duplicate = True
                        # Keep the longer, more specific one if current is shorter
                        if len(txt) > len(seen):
                            # Replace seen with current
                            for d in deduped:
                                if d["text"] == seen:
                                    d["text"] = txt
                                    d["score"] = max(d["score"], kw["score"])
                                    break
                            seen_texts[seen_texts.index(seen)] = txt
                        break
            if not is_duplicate:
                deduped.append(kw)
                seen_texts.append(txt)
        return deduped

    def _expand_acronyms(self, original_text: str, keywords: List[Dict]) -> List[Dict]:
        """Detect acronyms in original text and expand them in keywords."""
        # Pattern: "Full Name (ACRONYM)" or "ACRONYM (Full Name)"
        pattern1 = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})\s+\(([A-Z]{2,8})\)')
        pattern2 = re.compile(r'\b([A-Z]{2,8})\s+\(([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})\)')

        expansions: Dict[str, str] = {}
        for m in pattern1.finditer(original_text):
            full, acronym = m.group(1), m.group(2)
            expansions[acronym.lower()] = full.lower()
            expansions[full.lower()] = acronym.lower()
        for m in pattern2.finditer(original_text):
            acronym, full = m.group(1), m.group(2)
            expansions[acronym.lower()] = full.lower()
            expansions[full.lower()] = acronym.lower()

        # Also try naive acronym detection: all-caps words
        naive_acronyms = re.findall(r'\b([A-Z]{2,8})\b', original_text)
        for acr in naive_acronyms:
            acr_lower = acr.lower()
            if acr_lower not in expansions:
                # Look for preceding words that could form the expansion
                # This is heuristic: "... Convolutional Neural Network (CNN) ..."
                pass  # Too noisy without explicit parentheses

        enriched = []
        for kw in keywords:
            enriched.append(kw)
            txt = kw["text"]
            if txt in expansions:
                alt = expansions[txt]
                # Add alternate form if not already present
                if not any(k["text"] == alt for k in enriched):
                    enriched.append({
                        "text": alt,
                        "score": kw["score"] * 0.95,
                        "type": kw["type"],
                    })
        return enriched

    def _generate_synonyms(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Ask LLM for scientific synonyms of keywords."""
        if chat_completion is None or not keywords:
            return {}
        prompt = _SYNONYM_PROMPT.format(keywords="\n".join(f"- {k}" for k in keywords))
        try:
            raw = chat_completion(
                prompt,
                system="You suggest scientific synonyms. Respond ONLY with JSON.",
                max_tokens=400,
                temperature=0.2,
                top_p=0.9,
            )
            if not raw:
                return {}
            data = self._safe_json_parse(raw)
            syns = data.get("synonyms", {}) if isinstance(data, dict) else {}
            # Normalize to lowercase
            return {
                k.lower(): [str(v).strip().lower() for v in vals if v]
                for k, vals in syns.items()
                if isinstance(vals, list)
            }
        except Exception as exc:
            print(f"   [!] Synonym generation failed: {exc}")
            return {}

    def _fallback_token_extraction(self, text: str, top_n: int) -> List[Dict]:
        """Last-resort simple token extraction."""
        words = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", text.lower())
        counts: Dict[str, int] = {}
        for w in words:
            if w in _DOMAIN_STOPWORDS or len(w) <= 3:
                continue
            counts[w] = counts.get(w, 0) + 1
        sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"text": w, "score": 0.3, "type": "core"}
            for w, _ in sorted_words[:top_n]
        ]

    @staticmethod
    def _safe_json_parse(text: str) -> Optional[Dict]:
        """Parse JSON, stripping markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        try:
            return json.loads(text)
        except Exception:
            # Try to find the first JSON object
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            return None

    @staticmethod
    def _empty_result(elapsed_ms: int) -> Dict:
        return {
            "keywords": [],
            "synonyms": None,
            "provider": "fallback",
            "elapsed_ms": elapsed_ms,
        }
