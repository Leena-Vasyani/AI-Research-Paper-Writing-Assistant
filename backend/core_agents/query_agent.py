"""
Query Analysis Agent.

Provides intent classification, query decomposition, keyword extraction,
synonym expansion, and search strategy recommendation.
"""

from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from backend.core_agents.cache import query_cache
from backend.core_agents.keyword_agent import KeywordExtractionAgent

try:
    from backend.core_agents.llm_provider import chat_completion
except Exception:
    chat_completion = None  # type: ignore[assignment]


def _has_any_llm_provider() -> bool:
    """Fast check: are any LLM credentials configured?"""
    return bool(
        os.getenv("GROQ_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("OLLAMA_BASE_URL", "").strip()
    )

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_INTENT_CLASSIFICATION_PROMPT = """You are a research query classifier.
Classify the following research topic into exactly one of these intents:
- informational: seeking facts, explanations, or overview
- comparative: comparing methods, models, or approaches
- methodological: seeking how-to, implementation details, or algorithmic steps
- survey: seeking comprehensive literature review or state-of-the-art
- implementation: seeking code, tools, or practical deployment guidance

Respond ONLY with a JSON object: {{"intent": "informational", "confidence": 0.92}}
Do not include markdown or explanations.

Topic: {text}
"""

_DECOMPOSITION_PROMPT = """You are a research query decomposition assistant.
Break the following complex research topic into 1-3 simpler sub-queries that would help retrieve comprehensive literature.

Rules:
- Each sub-query should be self-contained and search-friendly.
- Return ONLY a JSON object: {{"sub_queries": ["sub query 1", "sub query 2"]}}
- If the topic is already simple and focused, return a single sub-query identical to the original.
- No markdown, no explanations.

Topic: {text}
"""

_SYNONYM_PROMPT = """You are a scientific terminology assistant.
For each keyword below, suggest 2-4 scientific synonyms or alternative phrasings used in academic literature.

Rules:
- Return ONLY a JSON object: {{"synonyms": {{"keyword1": ["alt1", "alt2"], ...}}}}
- Keep synonyms concise and academically relevant.
- No markdown, no explanations.

Keywords:
{keywords}
"""

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class QueryAnalysisAgent:
    """
    Analyzes research queries to produce enriched search metadata.

    Backward-compatible output keys:
        original_topic, keywords, subtopics, complexity_analysis

    New additive keys:
        intent, intent_confidence, sub_queries, synonyms,
        domain_specificity_score, scope, search_strategy
    """

    def __init__(self, keyword_agent: Optional[KeywordExtractionAgent] = None):
        self.keyword_agent = keyword_agent or KeywordExtractionAgent()
        self._has_llm = chat_completion is not None and _has_any_llm_provider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, text: str, top_keywords: int = 8) -> Dict[str, Any]:
        """
        Complete query analysis pipeline (synchronous).

        Args:
            text: Research topic or query text.
            top_keywords: Number of keywords to extract.

        Returns:
            Enriched dictionary with keywords, intent, strategy, etc.
        """
        start = time.time()
        text = (text or "").strip()
        if not text:
            return self._empty_result(text)

        # Cache lookup
        cache_key = f"{hash(text)}:{top_keywords}"
        cached = query_cache.get(cache_key)
        if cached is not None:
            cached["elapsed_ms"] = int((time.time() - start) * 1000)
            return cached

        print(f"   [>>] Analyzing query: '{text[:120]}...' " if len(text) > 120 else f"   [>>] Analyzing query: '{text}'")

        # Parallelize independent LLM/CPU tasks
        intent_result: Optional[Dict] = None
        keyword_result: Optional[Dict] = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_intent = executor.submit(self._classify_intent, text)
            future_keywords = executor.submit(
                self.keyword_agent.extract,
                text,
                top_n=top_keywords,
                use_llm=self._has_llm,
                expand_acronyms=True,
                return_synonyms=False,
            )
            intent_result = future_intent.result()
            keyword_result = future_keywords.result()

        keywords = keyword_result.get("keywords", []) if keyword_result else []
        keyword_texts = [k["text"] for k in keywords]

        # Decompose query
        sub_queries = self._decompose_query(text)

        # Expand subtopics (related keywords from the extracted set)
        subtopics = self._expand_subtopics(keywords)

        # Synonym expansion (parallel if LLM available)
        synonyms: Dict[str, List[str]] = {}
        if self._has_llm and keyword_texts:
            synonyms = self._generate_synonyms(keyword_texts[:6])

        # Complexity & domain analysis
        complexity = self._analyze_complexity(text, keywords)

        # Search strategy recommendation
        search_strategy = self._recommend_search_strategy(
            intent_result, complexity, len(keyword_texts)
        )

        elapsed_ms = int((time.time() - start) * 1000)

        result = {
            # Backward-compatible fields
            "original_topic": text,
            "keywords": keyword_texts,
            "subtopics": subtopics,
            "complexity_analysis": complexity,
            # New additive fields
            "intent": intent_result.get("intent", "informational") if intent_result else "informational",
            "intent_confidence": intent_result.get("confidence", 0.0) if intent_result else 0.0,
            "sub_queries": sub_queries,
            "synonyms": synonyms,
            "domain_specificity_score": complexity.get("domain_specificity_score", 0.0),
            "scope": complexity.get("scope", "narrow"),
            "search_strategy": search_strategy,
            "keyword_details": keywords,
            "elapsed_ms": elapsed_ms,
        }

        query_cache.set(cache_key, result)
        print(f"   [OK] Query analysis complete in {elapsed_ms}ms")
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Classify query intent using LLM."""
        if not self._has_llm:
            return None
        prompt = _INTENT_CLASSIFICATION_PROMPT.format(text=text[:2000])
        try:
            raw = chat_completion(
                prompt,
                system="You classify research queries. Respond ONLY with JSON.",
                max_tokens=80,
                temperature=0.1,
                top_p=0.9,
            )
            if not raw:
                return None
            data = self._safe_json_parse(raw)
            if isinstance(data, dict) and "intent" in data:
                intent = str(data["intent"]).strip().lower()
                confidence = float(data.get("confidence", 0.5))
                valid_intents = {"informational", "comparative", "methodological", "survey", "implementation"}
                if intent not in valid_intents:
                    intent = "informational"
                return {"intent": intent, "confidence": confidence}
        except Exception as exc:
            print(f"   [!] Intent classification failed: {exc}")
        return None

    def _decompose_query(self, text: str) -> List[str]:
        """Break complex queries into simpler sub-queries using LLM."""
        if not self._has_llm:
            return [text]
        prompt = _DECOMPOSITION_PROMPT.format(text=text[:2000])
        try:
            raw = chat_completion(
                prompt,
                system="You decompose research queries. Respond ONLY with JSON.",
                max_tokens=200,
                temperature=0.2,
                top_p=0.9,
            )
            if not raw:
                return [text]
            data = self._safe_json_parse(raw)
            if isinstance(data, dict):
                sub_queries = data.get("sub_queries", [])
                if isinstance(sub_queries, list) and sub_queries:
                    return [str(s).strip() for s in sub_queries if str(s).strip()]
        except Exception as exc:
            print(f"   [!] Query decomposition failed: {exc}")
        return [text]

    def _expand_subtopics(self, keywords: List[Dict]) -> Dict[str, List[str]]:
        """Map each keyword to its most semantically related peers from the set."""
        if not keywords or len(keywords) < 2:
            return {k["text"]: [] for k in keywords}
        texts = [k["text"] for k in keywords]
        # Simple co-occurrence heuristic: longer keywords share subterms
        subtopics: Dict[str, List[str]] = {}
        for i, kw in enumerate(texts):
            related = []
            kw_words = set(kw.split())
            for j, other in enumerate(texts):
                if i == j:
                    continue
                other_words = set(other.split())
                overlap = len(kw_words & other_words)
                if overlap > 0:
                    related.append((other, overlap))
            # Sort by word overlap
            related.sort(key=lambda x: x[1], reverse=True)
            subtopics[kw] = [r[0] for r in related[:3]]
        return subtopics

    def _generate_synonyms(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Use LLM to generate scientific synonyms for keywords."""
        if not self._has_llm or not keywords:
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
            return {
                k.lower(): [str(v).strip().lower() for v in vals if v]
                for k, vals in syns.items()
                if isinstance(vals, list)
            }
        except Exception as exc:
            print(f"   [!] Synonym generation failed: {exc}")
            return {}

    def _analyze_complexity(self, text: str, keywords: List[Dict]) -> Dict[str, Any]:
        """
        Analyze query complexity using keyword diversity and domain specificity.
        Replaces the old word-count heuristic.
        """
        words = text.split()
        word_count = len(words)
        unique_words = len(set(w.lower().strip(".,;:!?") for w in words))
        lexical_diversity = unique_words / max(word_count, 1)

        # Domain specificity: ratio of technical/multi-word keywords
        technical_count = sum(1 for k in keywords if k.get("type") in ("method", "domain", "entity"))
        domain_specificity_score = min(technical_count / max(len(keywords), 1), 1.0)

        # Scope estimation
        if word_count <= 4 and len(keywords) <= 3:
            scope = "narrow"
        elif word_count > 12 or len(keywords) > 7:
            scope = "interdisciplinary"
        else:
            scope = "broad"

        # Recommended papers based on scope and diversity
        if scope == "narrow":
            recommended_papers = 5
        elif scope == "broad":
            recommended_papers = 7
        else:
            recommended_papers = 10

        # Estimated complexity label
        if domain_specificity_score > 0.6 and lexical_diversity > 0.7:
            estimated_complexity = "high"
        elif domain_specificity_score > 0.3 or lexical_diversity > 0.5:
            estimated_complexity = "medium"
        else:
            estimated_complexity = "low"

        return {
            "word_count": word_count,
            "lexical_diversity": round(lexical_diversity, 3),
            "domain_specificity_score": round(domain_specificity_score, 3),
            "estimated_complexity": estimated_complexity,
            "is_specific": domain_specificity_score > 0.4,
            "scope": scope,
            "recommended_papers": recommended_papers,
        }

    def _recommend_search_strategy(
        self,
        intent: Optional[Dict],
        complexity: Dict[str, Any],
        keyword_count: int,
    ) -> Dict[str, Any]:
        """Recommend retrieval parameters based on query analysis."""
        intent_str = intent.get("intent", "informational") if intent else "informational"
        scope = complexity.get("scope", "broad")

        # Base recommendations
        max_results = complexity.get("recommended_papers", 7)
        use_multi_query = scope in ("broad", "interdisciplinary") or keyword_count >= 5

        # Source selection
        sources = ["arxiv", "openalex", "semantic_scholar"]
        if intent_str in ("implementation", "methodological"):
            # arXiv and Semantic Scholar often have better CS/Engineering coverage
            sources = ["arxiv", "semantic_scholar", "openalex"]
        elif intent_str == "survey":
            # OpenAlex good for broad survey coverage
            sources = ["openalex", "semantic_scholar", "arxiv"]

        return {
            "max_results": max_results,
            "use_multi_query": use_multi_query,
            "sources": sources,
            "recommended_top_keywords": min(keyword_count + 2, 12),
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_json_parse(text: str) -> Optional[Dict]:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```\w*\n?', '', text)
            text = re.sub(r'\n?```$', '', text)
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            return None

    @staticmethod
    def _empty_result(text: str) -> Dict[str, Any]:
        return {
            "original_topic": text,
            "keywords": [],
            "subtopics": {},
            "complexity_analysis": {
                "word_count": 0,
                "lexical_diversity": 0.0,
                "domain_specificity_score": 0.0,
                "estimated_complexity": "low",
                "is_specific": False,
                "scope": "narrow",
                "recommended_papers": 5,
            },
            "intent": "informational",
            "intent_confidence": 0.0,
            "sub_queries": [],
            "synonyms": {},
            "domain_specificity_score": 0.0,
            "scope": "narrow",
            "search_strategy": {
                "max_results": 5,
                "use_multi_query": False,
                "sources": ["arxiv", "openalex", "semantic_scholar"],
                "recommended_top_keywords": 8,
            },
            "keyword_details": [],
            "elapsed_ms": 0,
        }


# Keep backward-compatible alias for existing imports
ScientificQueryAgent = QueryAnalysisAgent
