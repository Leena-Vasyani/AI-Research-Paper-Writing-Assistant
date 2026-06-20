"""
Fast, LLM-powered paper summarization agent.

Strategy:
  1. Abstract-first: use abstracts already available from retrieval agents.
  2. Parallel PDF fallback: only download full PDFs for papers with short abstracts.
  3. Single-pass LLM summarization: one call generates executive summary,
     section synthesis, key insights, gaps, and overall synthesis.
  4. Aggressive caching: summaries keyed by paper-hash + keywords.
  5. Zero artificial delays.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import requests as _requests

from backend.core_agents.cache import retrieval_cache

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

try:
    import PyPDF2
except Exception:
    PyPDF2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SUMMARY_PROMPT = """You are an expert academic research synthesizer.
Read the following paper abstracts and produce a structured synthesis.

Rules:
- Use ONLY the information provided in the abstracts.
- Do NOT invent facts, citations, or paper titles.
- Respond ONLY with valid JSON matching the schema below.
- Keep summaries concise, factual, and academically neutral.

Schema:
{{
  "executive_summary": "2-3 paragraph overview of the collective research",
  "section_summaries": {{
    "Research Context and Background": "...",
    "Methodological Approaches": "...",
    "Key Findings and Results": "...",
    "Analysis and Discussion": "...",
    "Conclusions and Future Directions": "..."
  }},
  "key_insights": {{
    "methodological_approaches": ["...", "..."],
    "major_findings": ["...", "..."],
    "innovative_contributions": ["...", "..."],
    "practical_applications": ["...", "..."],
    "limitations_challenges": ["...", "..."]
  }},
  "research_gaps": ["...", "...", "..."],
  "synthesis": "1 paragraph final synthesis statement"
}}

Keywords: {keywords}

Papers:
{papers}

Return ONLY the JSON object, no markdown fences or explanations.
"""

_FALLBACK_PROMPT = """Summarize the following research abstracts into a concise academic synthesis.

Keywords: {keywords}

Abstracts:
{abstracts}

Provide:
1. Executive Summary (2 paragraphs)
2. Methodological Approaches (1 paragraph)
3. Key Findings (1 paragraph)
4. Research Gaps (bullet list)
5. Final Synthesis (1 paragraph)
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class PaperSummarizationAgent:
    """
    Fast summarization using abstracts + optional parallel PDF fallback.
    Falls back to simple truncation if all LLM providers fail.
    """

    def __init__(self, use_api: bool = True):
        self.use_api = use_api
        self._session = _requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_comprehensive_summary(
        self, papers: List[Dict[str, Any]], keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of all papers.
        Tries single-pass LLM synthesis; falls back to heuristics if unavailable.
        """
        start = time.time()
        if not papers:
            return self._create_empty_summary([], keywords)

        # --- Cache lookup ---
        cache_key = self._make_cache_key(papers, keywords)
        cached = retrieval_cache.get(cache_key)
        if cached is not None:
            print(f"   [OK] Summary cache hit")
            return cached

        print(f"\n   [>>] Summarizing {len(papers)} papers...")

        # --- Gather text corpus (abstract-first) ---
        texts, metadata = self._gather_texts(papers)

        if not texts:
            return self._create_empty_summary(papers, keywords)

        # --- Try LLM single-pass synthesis ---
        result: Optional[Dict[str, Any]] = None
        if self.use_api and chat_completion is not None:
            result = self._llm_synthesize(texts, keywords, metadata)

        # --- Fallback: heuristic summary ---
        if result is None:
            result = self._heuristic_synthesize(texts, keywords, metadata)

        result["metadata"] = {
            "total_papers": len(papers),
            "papers_with_full_text": sum(1 for t in texts if len(t) > 1500),
            "keywords": keywords,
            "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "papers_analyzed": metadata,
        }

        elapsed = int((time.time() - start) * 1000)
        print(f"   [OK] Summary generated in {elapsed}ms")

        retrieval_cache.set(cache_key, result)
        return result

    # ------------------------------------------------------------------
    # Text gathering: abstract-first with parallel PDF fallback
    # ------------------------------------------------------------------

    def _gather_texts(
        self, papers: List[Dict[str, Any]], min_abstract_len: int = 300
    ) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Collect best available text for each paper.
        Uses abstract if long enough; otherwise downloads PDF in parallel.
        """
        texts: List[str] = []
        metadata: List[Dict[str, str]] = []
        need_pdf: List[Tuple[int, Dict[str, Any]]] = []

        for idx, paper in enumerate(papers):
            abstract = (paper.get("abstract") or "").strip()
            title = paper.get("title", f"Paper {idx+1}")
            meta = {
                "title": title,
                "authors": paper.get("authors_str", "Unknown"),
                "published": paper.get("published", "Unknown"),
                "url": paper.get("pdf_url", ""),
                "abstract": abstract,
            }
            metadata.append(meta)

            if len(abstract) >= min_abstract_len:
                texts.append(abstract)
            else:
                texts.append("")  # placeholder
                pdf_url = paper.get("pdf_url", "")
                if pdf_url and pdf_url.startswith("http"):
                    need_pdf.append((idx, paper))
                else:
                    texts[-1] = abstract  # use short abstract anyway

        # Parallel PDF download for papers with short abstracts
        if need_pdf:
            print(f"   [>>] Downloading {len(need_pdf)} PDFs in parallel...")
            with ThreadPoolExecutor(max_workers=min(len(need_pdf), 4)) as executor:
                futures = {
                    executor.submit(self._download_pdf_text, p.get("pdf_url", "")): idx
                    for idx, p in need_pdf
                }
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        pdf_text = future.result()
                        if pdf_text and len(pdf_text) > 500:
                            texts[idx] = pdf_text
                    except Exception as exc:
                        print(f"   [!] PDF download failed for paper {idx}: {exc}")

        # Filter out empty texts
        valid_texts = [t for t in texts if t]
        return valid_texts, metadata

    def _download_pdf_text(self, pdf_url: str, max_pages: int = 20) -> str:
        """Download and extract text from a PDF URL."""
        if not pdf_url or not pdf_url.startswith("http"):
            return ""
        if PyPDF2 is None:
            return ""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        for attempt in range(2):
            try:
                response = self._session.get(pdf_url, timeout=15, headers=headers)
                response.raise_for_status()
                break
            except Exception:
                if attempt == 1:
                    return ""
                # NO artificial sleep here
        else:
            return ""

        try:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = ""
            pages_to_extract = min(len(pdf_reader.pages), max_pages)
            for page_num in range(pages_to_extract):
                try:
                    text = pdf_reader.pages[page_num].extract_text() or ""
                    if len(text.strip()) > 50:
                        full_text += text + "\n"
                except Exception:
                    continue
            return full_text.strip()
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # LLM single-pass synthesis
    # ------------------------------------------------------------------

    def _llm_synthesize(
        self, texts: List[str], keywords: List[str], metadata: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """Single LLM call to synthesize all paper texts."""
        if chat_completion is None or not _has_any_llm_provider():
            return None

        # Build compact paper descriptions
        paper_blocks = []
        for i, (text, meta) in enumerate(zip(texts, metadata)):
            snippet = text[:2000].replace("\n", " ")
            block = f"Paper {i+1}: {meta['title']}\nAbstract/Snippet: {snippet}\n"
            paper_blocks.append(block)

        papers_str = "\n---\n".join(paper_blocks)
        prompt = _SUMMARY_PROMPT.format(
            keywords=", ".join(keywords),
            papers=papers_str,
        )

        try:
            raw = chat_completion(
                prompt,
                system="You synthesize academic research. Respond ONLY with JSON.",
                max_tokens=2500,
                temperature=0.2,
                top_p=0.9,
            )
            if not raw:
                return None
            data = self._safe_json_parse(raw)
            if not data:
                return None

            # Validate and normalize structure
            return {
                "executive_summary": data.get("executive_summary", ""),
                "section_summaries": data.get("section_summaries", {}),
                "key_insights": data.get("key_insights", {}),
                "research_gaps": data.get("research_gaps", []),
                "synthesis": data.get("synthesis", ""),
            }
        except Exception as exc:
            print(f"   [!] LLM synthesis failed: {exc}")
            return None

    # ------------------------------------------------------------------
    # Heuristic fallback (no LLM available)
    # ------------------------------------------------------------------

    def _heuristic_synthesize(
        self, texts: List[str], keywords: List[str], metadata: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Fast heuristic summary when LLM is unavailable."""
        combined = " ".join(texts)
        sentences = self._split_sentences(combined)

        # Score sentences by keyword overlap
        scored = []
        for s in sentences:
            score = sum(1 for kw in keywords if kw.lower() in s.lower())
            scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)

        top_sentences = [s for _, s in scored[:15]]
        executive = " ".join(top_sentences[:5])

        # Dynamic keyword-based insights (no hardcoded stock market text)
        insights = {
            "methodological_approaches": [
                f"Research addresses topics related to {keywords[0]}" if keywords else "Various methods are employed"
            ],
            "major_findings": [
                f"Studies demonstrate progress in {', '.join(keywords[:2])}" if len(keywords) >= 2 else "Key findings reported"
            ],
            "innovative_contributions": ["Novel approaches and techniques are explored"],
            "practical_applications": [f"Applications in {keywords[0]} domain" if keywords else "Practical implications discussed"],
            "limitations_challenges": ["Challenges include data quality, scalability, and generalization"],
        }

        return {
            "executive_summary": executive,
            "section_summaries": {
                "Research Context and Background": f"This research explores {', '.join(keywords[:3])}.",
                "Methodological Approaches": "Multiple methodologies are employed across the reviewed papers.",
                "Key Findings and Results": "Significant findings are reported with measurable improvements.",
                "Analysis and Discussion": "Authors discuss implications, trade-offs, and future directions.",
                "Conclusions and Future Directions": "Further research is needed to address identified gaps.",
            },
            "key_insights": insights,
            "research_gaps": [
                f"Need for larger-scale studies in {keywords[0]}" if keywords else "Need for larger-scale studies",
                "Improved evaluation benchmarks and standardized datasets",
                "Better interpretability and reproducibility of results",
            ],
            "synthesis": f"This synthesis covers research on {', '.join(keywords[:3])}. The field shows active development with both promising results and open challenges.",
        }

    # ------------------------------------------------------------------
    # Empty summary
    # ------------------------------------------------------------------

    def _create_empty_summary(self, papers: List[Dict], keywords: List[str]) -> Dict[str, Any]:
        topic = ", ".join(keywords[:3]) if keywords else "the selected topic"
        return {
            "metadata": {
                "total_papers": len(papers),
                "papers_with_full_text": 0,
                "keywords": keywords,
                "analysis_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "papers_analyzed": [{
                    "title": p.get("title", "Unknown"),
                    "authors": p.get("authors_str", "Unknown"),
                    "published": p.get("published", "Unknown"),
                    "url": p.get("pdf_url", ""),
                    "abstract": p.get("abstract", ""),
                } for p in papers],
            },
            "executive_summary": f"This analysis covers {len(papers)} papers on {topic}. Insufficient text was available to generate a detailed summary.",
            "section_summaries": {
                "Research Context and Background": f"Research explores various aspects of {topic}.",
                "Methodological Approaches": "Methodologies vary across the included studies.",
                "Key Findings and Results": "Findings are reported in the original papers.",
                "Analysis and Discussion": "Discussion points are available in source materials.",
                "Conclusions and Future Directions": "Further research is encouraged.",
            },
            "key_insights": {
                "methodological_approaches": ["See individual papers for details"],
                "major_findings": ["See individual papers for details"],
                "innovative_contributions": ["See individual papers for details"],
                "practical_applications": ["See individual papers for details"],
                "limitations_challenges": ["See individual papers for details"],
            },
            "research_gaps": ["Detailed analysis requires full-text access"],
            "synthesis": f"A synthesis of {len(papers)} papers on {topic}. Full text extraction is needed for deeper insights.",
        }

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        if not text:
            return []
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        cleaned = []
        for s in sentences:
            s = re.sub(r'\s+', ' ', s).strip()
            if 30 <= len(s) <= 400:
                cleaned.append(s)
        return cleaned

    @staticmethod
    def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
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
    def _make_cache_key(papers: List[Dict], keywords: List[str]) -> str:
        paper_ids = "|".join(sorted(
            p.get("entry_id", p.get("title", "")) for p in papers
        ))
        payload = f"{paper_ids}:{','.join(sorted(keywords))}"
        return hashlib.sha256(payload.encode()).hexdigest()[:32]
