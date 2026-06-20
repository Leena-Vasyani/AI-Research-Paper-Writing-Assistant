"""
High-performance paper retrieval agent.

Inspired by PaperPlain MCP — adds domain-based routing, PubMed integration,
citation counts, source-status tracking, and smart cross-source deduplication.

Sources:
  - arXiv (CS/AI/physics)
  - PubMed (health/medicine/biology) — free NCBI E-utilities
  - OpenAlex (general academic)
  - Semantic Scholar (general academic + citation counts)
  - CrossRef (cross-discipline metadata + reference lists for the Citation Graph)

Features:
  - Domain classifier routes health → PubMed, CS → arXiv, general → all
  - Parallel source fetching with per-source status tracking
  - Cross-source deduplication by URL and DOI (+ optional semantic near-dup merge)
  - Citation counts from Semantic Scholar/CrossRef/OpenAlex, sorted by impact
  - Emits a shared Citation Graph consumed by the Outline and Review agents
  - Two-tier caching (memory + optional Redis)
  - Connection pooling and zero artificial delays
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import requests as _requests

from backend.core_agents.cache import retrieval_cache
from backend.core_agents.knowledge.citation_graph import CitationGraph

try:
    from backend.core_agents.keyword_agent import KeywordExtractionAgent
except Exception:
    KeywordExtractionAgent = None  # type: ignore[misc,assignment]

try:
    import arxiv
except Exception:
    arxiv = None  # type: ignore[assignment]

import os


# ---------------------------------------------------------------------------
# Optional semantic embedding model (lazy, shared) for near-dup merge + relevance.
# Gracefully degrades to the lexical path if sentence-transformers is unavailable.
# ---------------------------------------------------------------------------

_EMBED_MODEL: Any = None
_EMBED_DISABLED = False
_EMBED_MODEL_NAME = os.getenv("SEARCH_EMBED_MODEL", "all-MiniLM-L6-v2")


def _get_embed_model() -> Any:
    """Lazily load (and cache) the sentence-transformer; None if unavailable."""
    global _EMBED_MODEL, _EMBED_DISABLED
    if _EMBED_DISABLED:
        return None
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer(_EMBED_MODEL_NAME)
    except Exception as exc:  # noqa: BLE001 - optional dependency
        print(f"   [!] Semantic search disabled (embeddings unavailable): {exc}")
        _EMBED_DISABLED = True
        _EMBED_MODEL = None
    return _EMBED_MODEL

# ---------------------------------------------------------------------------
# Domain classifier (keyword-based, zero LLM calls)
# ---------------------------------------------------------------------------

_HEALTH_RE = re.compile(
    r"\b(sleep|insomnia|anxiety|anxious|stress|depress|pain|ache|headache|migraine|"
    r"diet|nutrition|weight|obese|exercise|fatigue|tired|focus|adhd|autism|cancer|diabetes|"
    r"blood|pressure|heart|cholesterol|vitamin|supplement|immune|gut|digestion|mental health|"
    r"therapy|meditation|mindfulness|mood|burnout|inflammation|allergy|asthma|skin|aging|"
    r"memory|alzheimer|cognitive|brain|alcohol|smoking|addiction|symptoms|treatment|medicine|"
    r"medication|dose|chronic|surgery|vaccine|antibiot|clinical|patient|disease|disorder|"
    r"syndrome|injury|rehabilitation|psychiatric|neurol|cardio|oncol|gastro|pediatr|geriatric|"
    r"healthcare|hospital|epidemic|pandemic|virus|bacteria|infection|pathogen|genome|"
    r"protein|cell|tissue|organ|biomarker|diagnosis|prognosis|radiology|imaging|mri|ct scan|"
    r"surgery|transplant|immunotherapy|gene therapy|stem cell|pharma|drug|trial|placebo|"
    r"cohort|retrospective|prospective|meta.analysis|systematic review|pubmed|medline|"
    r"who|fda|cdc|nih|biomedical|bioinformatics|medical imaging|electronic health record|ehr|"
    r"precision medicine|personalized medicine|telemedicine|digital health|wearable)\b",
    re.IGNORECASE,
)

_CS_RE = re.compile(
    r"\b(algorithm|neural network|machine learning|deep learning|transformer|llm|"
    r"large language model|language model|reinforcement|classification|clustering|regression|"
    r"computer vision|nlp|natural language|robotics|autonomous|blockchain|cryptograph|"
    r"database|distributed|cloud|microservice|compiler|operating system|cybersecurity|"
    r"quantum comput|software engineer|retrieval|embedding|vector|attention|fine.tun|prompt|"
    r"inference|benchmark|agentic|multi.agent|smart grid|demand response|energy management|"
    r"HEMS|home energy|building energy|V2G|vehicle.to.grid|EV charging|electric vehicle|"
    r"battery storage|renewable energy|solar|wind power|forecasting|optimization|scheduling|"
    r"control system|model predictive|reinforcement learning|arxiv|preprint|neurips|icml|"
    r"iclr|cvpr|acl|emnlp|aaai|ijcai|kdd|sigmod|vldb|osdi|sosp|pldi|oopsla|usenix|"
    r"tensorflow|pytorch|jax|hugging face|openai|anthropic|gemini|gpt|claude|"
    r"diffusion|gan|vae|cnn|rnn|lstm|gru|bert|roberta|t5|gpt.3|gpt.4|llama|mistral|"
    r"mixtral|gemma|phi|qwen|yi|falcon|mamba|mambaout|state space|moe|mixture of experts)\b",
    re.IGNORECASE,
)


def _classify_domain(query: str) -> str:
    """Classify a query into 'health', 'cs', or 'general' using keyword regex."""
    if _CS_RE.search(query):
        return "cs"
    if _HEALTH_RE.search(query):
        return "health"
    return "general"


class SearchAgent:
    """
    Search Agent — real-time literature discovery across multiple scholarly
    sources with parallel fetching, caching, cross-source + semantic dedup,
    citation-aware ranking, and Citation Graph emission.

    (Formerly ``PaperRetrievalAgent``; the old name remains as an alias.)
    """

    def __init__(
        self,
        keyword_agent: Optional[KeywordExtractionAgent] = None,
        min_relevance_score: float = 0.5,
        min_year: int = 2020,
        use_semantic: bool = True,
    ):
        self.keyword_agent = keyword_agent
        self.min_relevance_score = min_relevance_score
        self.min_year = min_year
        self.use_semantic = use_semantic
        self.http_timeout = 12  # reduced from 20s
        self.openalex_api_key = os.getenv("OPENALEX_API_KEY", "").strip()
        self.openalex_email = os.getenv("OPENALEX_EMAIL", "").strip()
        self.semantic_scholar_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
        self.crossref_mailto = (
            os.getenv("CROSSREF_MAILTO", "").strip() or self.openalex_email or ""
        )

        # Reusable HTTP session for connection pooling
        self._session = _requests.Session()
        self._session.headers.update({
            "User-Agent": "ResearchGen/0.1 (mailto:{})".format(
                self.openalex_email or "support@example.com"
            )
        })

        # arXiv client (lazy init if package missing)
        self._arxiv_client: Optional[Any] = None

    # ------------------------------------------------------------------
    # arXiv client lazy init
    # ------------------------------------------------------------------

    def _arxiv(self) -> Optional[Any]:
        if self._arxiv_client is None and arxiv is not None:
            self._arxiv_client = arxiv.Client()
        return self._arxiv_client

    # ------------------------------------------------------------------
    # Query building
    # ------------------------------------------------------------------

    def build_search_query(
        self,
        keywords: List[str],
        max_keywords: int = 5,
        synonyms: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """
        Build an optimized search query from keywords.
        Uses synonyms if available to broaden coverage.
        """
        top_keywords = [k for k in keywords if k and k.strip()][:max_keywords]
        if not top_keywords:
            # Fallback: search for recent papers broadly so we don't crash APIs
            return "cat:cs.* OR cat:q-bio.* OR cat:stat.ML"

        parts: List[str] = []
        for kw in top_keywords:
            kw_phrase = f'"{kw}"'
            alt_terms: List[str] = []
            if synonyms:
                alt_terms = [f'"{s}"' for s in synonyms.get(kw, [])[:2]]
            if alt_terms:
                parts.append(f"({kw_phrase} OR {' OR '.join(alt_terms)})")
            else:
                parts.append(kw_phrase)

        # Join with OR for broader recall; AND would be too restrictive for multi-source APIs
        return " OR ".join(parts)

    def enrich_keywords_from_topic(self, topic: str, top_n: int = 8) -> Dict[str, Any]:
        """
        Use KeywordExtractionAgent to extract high-quality keywords + synonyms
        from a raw research topic string.
        """
        if self.keyword_agent is None:
            return {"keywords": [], "synonyms": {}}
        result = self.keyword_agent.extract(
            text=topic,
            top_n=top_n,
            use_llm=False,  # fast embedding path; avoids slow LLM fallback chain
            expand_acronyms=True,
            return_synonyms=True,
        )
        return {
            "keywords": [k["text"] for k in result.get("keywords", [])],
            "synonyms": result.get("synonyms") or {},
            "provider": result.get("provider", "fallback"),
        }

    # ------------------------------------------------------------------
    # Relevance scoring
    # ------------------------------------------------------------------

    def calculate_relevance_score(self, paper: Dict, keywords: List[str]) -> float:
        title_lower = (paper.get("title") or "").lower()
        abstract_lower = (paper.get("abstract") or "").lower()

        score = 0.0
        max_score = 0

        for keyword in keywords:
            kw_lower = keyword.lower()
            max_score += 0.5

            # Exact match in title
            if kw_lower in title_lower:
                score += 0.5
            elif " " in kw_lower:
                words = kw_lower.split()
                word_matches = sum(1 for w in words if w in title_lower)
                if word_matches >= len(words) - 1:
                    score += 0.3

            # Abstract match
            if kw_lower in abstract_lower:
                score += 0.2
            elif " " in kw_lower:
                words = kw_lower.split()
                word_matches = sum(1 for w in words if w in abstract_lower)
                if word_matches >= len(words) - 1:
                    score += 0.1

        return min(score / max_score, 1.0) if max_score > 0 else 0.5

    def is_recent_paper(self, published_date: str) -> bool:
        try:
            year = int(str(published_date).split("-")[0])
            return year >= self.min_year
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Source fetchers
    # ------------------------------------------------------------------

    def _retrieve_arxiv(self, keywords: List[str], max_results: int, synonyms: Optional[Dict[str, List[str]]] = None, raw_query: Optional[str] = None) -> List[Dict]:
        client = self._arxiv()
        if client is None or arxiv is None:
            return []

        # arXiv supports boolean syntax natively, so a raw boolean string is used as-is.
        search_query = raw_query or self.build_search_query(keywords, synonyms=synonyms)

        def _do_search(query: str, limit: int) -> List[Dict]:
            out: List[Dict] = []
            search = arxiv.Search(
                query=query,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance,
                sort_order=arxiv.SortOrder.Descending,
            )
            for result in client.results(search):
                out.append({
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "authors_str": ", ".join([author.name for author in result.authors][:3]),
                    "abstract": result.summary,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "query_used": query,
                    "retrieved_at": datetime.now().isoformat(),
                    "source": "arxiv",
                    "doi": "",
                    "url": result.entry_id.replace("http://arxiv.org/abs/", "https://arxiv.org/abs/"),
                    "citations": 0,
                })
                if len(out) >= limit:
                    break
            return out

        papers: List[Dict] = []
        try:
            papers = _do_search(search_query, max_results * 2)
            # Fallback: if broad search returns nothing, retry with title-field search
            if not papers:
                title_query = search_query.replace('"', '')
                papers = _do_search(f"ti:{title_query}", max_results * 2)
        except Exception as e:
            print(f"   [!] arXiv retrieval failed: {e}")
        return papers

    def _retrieve_openalex(self, keywords: List[str], max_results: int, synonyms: Optional[Dict[str, List[str]]] = None) -> List[Dict]:
        search_query = self.build_search_query(keywords, synonyms=synonyms)
        url = "https://api.openalex.org/works"
        params: Dict[str, Any] = {
            "search": search_query,
            "per-page": min(max_results * 2, 100),  # reduced from *4 / 200
            "sort": "relevance_score:desc",
        }
        if self.openalex_api_key:
            params["api_key"] = self.openalex_api_key
        if self.openalex_email:
            params["mailto"] = self.openalex_email

        papers: List[Dict] = []
        try:
            response = self._session.get(url, params=params, timeout=self.http_timeout)
            response.raise_for_status()
            data = response.json()
            for item in data.get("results", []):
                title = item.get("title") or ""
                if not title:
                    continue

                authors = []
                for auth in item.get("authorships", [])[:6]:
                    name = (auth.get("author") or {}).get("display_name")
                    if name:
                        authors.append(name)

                publication_date = item.get("publication_date") or ""
                doi = item.get("doi") or ""
                if doi.startswith("https://doi.org/"):
                    doi = doi.replace("https://doi.org/", "")

                primary_location = item.get("primary_location") or {}
                open_access = item.get("open_access") or {}
                pdf_url = open_access.get("oa_url") or primary_location.get("pdf_url") or ""
                landing_url = primary_location.get("landing_page_url") or item.get("id") or ""

                # Citation count from OpenAlex
                cited_by_count = item.get("cited_by_count") or 0
                papers.append({
                    "title": title,
                    "authors": authors,
                    "authors_str": ", ".join(authors[:3]) if authors else "Unknown Author",
                    "abstract": self._extract_openalex_abstract(item.get("abstract_inverted_index")),
                    "published": publication_date,
                    "pdf_url": pdf_url,
                    "entry_id": item.get("id", ""),
                    "categories": [
                        (item.get("primary_topic") or {}).get("display_name", "")
                    ],
                    "primary_category": (item.get("primary_topic") or {}).get("display_name", "openalex"),
                    "query_used": search_query,
                    "retrieved_at": datetime.now().isoformat(),
                    "source": "openalex",
                    "doi": doi,
                    "url": landing_url,
                    "citations": cited_by_count,
                })
                if len(papers) >= max_results:
                    break
        except Exception as e:
            print(f"   [!] OpenAlex retrieval failed: {e}")
        return papers

    def _retrieve_semantic_scholar(self, keywords: List[str], max_results: int, synonyms: Optional[Dict[str, List[str]]] = None, raw_query: Optional[str] = None) -> List[Dict]:
        # Semantic Scholar is keyword-based; a stripped (operator-free) query is passed in.
        search_query = raw_query or self.build_search_query(keywords, synonyms=synonyms)
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        # Use lower limit when no API key to respect rate limits
        limit = min(max_results, 10) if not self.semantic_scholar_api_key else min(max_results * 2, 50)
        params: Dict[str, Any] = {
            "query": search_query,
            "limit": limit,
            "fields": "title,abstract,authors,year,venue,url,externalIds,openAccessPdf,publicationDate",
        }
        headers: Dict[str, str] = {}
        if self.semantic_scholar_api_key:
            headers["x-api-key"] = self.semantic_scholar_api_key

        papers: List[Dict] = []
        retries = 2 if not self.semantic_scholar_api_key else 0
        for attempt in range(retries + 1):
            try:
                response = self._session.get(url, params=params, headers=headers, timeout=self.http_timeout)
                if response.status_code == 429:
                    if attempt < retries:
                        import time
                        wait = 0.8 * (attempt + 1)
                        print(f"   [!] Semantic Scholar rate-limited (429); retrying in {wait:.1f}s...")
                        time.sleep(wait)
                        continue
                    print("   [!] Semantic Scholar rate-limited (429); skipping. Add SEMANTIC_SCHOLAR_API_KEY to raise limits.")
                    break
                response.raise_for_status()
                data = response.json()
                for item in data.get("data", []):
                    title = item.get("title") or ""
                    if not title:
                        continue

                    authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
                    year = item.get("year")
                    published = item.get("publicationDate") or (f"{year}-01-01" if year else "")

                    external_ids = item.get("externalIds") or {}
                    doi = external_ids.get("DOI", "")
                    open_access_pdf = item.get("openAccessPdf") or {}

                    papers.append({
                        "title": title,
                        "authors": authors,
                        "authors_str": ", ".join(authors[:3]) if authors else "Unknown Author",
                        "abstract": item.get("abstract", "") or "",
                        "published": published,
                        "pdf_url": open_access_pdf.get("url", ""),
                        "entry_id": item.get("paperId", ""),
                        "categories": [item.get("venue", "")],
                        "primary_category": item.get("venue", "semantic_scholar") or "semantic_scholar",
                        "query_used": search_query,
                        "retrieved_at": datetime.now().isoformat(),
                        "source": "semantic_scholar",
                        "doi": doi,
                        "url": item.get("url", ""),
                        "citations": item.get("citationCount") or 0,
                    })
                    if len(papers) >= max_results:
                        break
                break  # success — exit retry loop
            except Exception as e:
                print(f"   [!] Semantic Scholar retrieval failed: {e}")
                break
        return papers

    def _extract_openalex_abstract(self, abstract_index: Optional[Dict]) -> str:
        if not abstract_index or not isinstance(abstract_index, dict):
            return ""
        positions: Dict[int, str] = {}
        for token, idxs in abstract_index.items():
            if not isinstance(idxs, list):
                continue
            for idx in idxs:
                if isinstance(idx, int):
                    positions[idx] = token
        if not positions:
            return ""
        return " ".join(token for _, token in sorted(positions.items(), key=lambda x: x[0]))

    # ------------------------------------------------------------------
    # PubMed (NCBI E-utilities — free, no API key)
    # ------------------------------------------------------------------

    def _retrieve_pubmed(self, keywords: List[str], max_results: int, synonyms: Optional[Dict[str, List[str]]] = None) -> List[Dict]:
        """Search PubMed via NCBI E-utilities: esearch → esummary → efetch."""
        search_query = self.build_search_query(keywords, synonyms=synonyms)
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        params_tool = "tool=researchgen&email=researchgen@example.com"

        papers: List[Dict] = []
        try:
            # Step 1: esearch — get PMIDs
            esearch_url = f"{base}/esearch.fcgi?db=pubmed&term={_requests.utils.quote(search_query)}&retmax={max_results * 2}&retmode=json&sort=relevance&{params_tool}"
            search_resp = self._session.get(esearch_url, timeout=self.http_timeout)
            search_resp.raise_for_status()
            pmids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not pmids:
                return []

            # Step 2: esummary — get metadata
            esummary_url = f"{base}/esummary.fcgi?db=pubmed&id={','.join(pmids)}&retmode=json&{params_tool}"
            summary_resp = self._session.get(esummary_url, timeout=self.http_timeout)
            summary_resp.raise_for_status()
            summary_data = summary_resp.json().get("result", {})

            # Step 3: efetch — get abstracts
            abstracts = self._fetch_pubmed_abstracts(pmids)

            for pmid in pmids:
                item = summary_data.get(pmid)
                if not item or not item.get("title"):
                    continue
                abstract = abstracts.get(pmid, "")
                if not abstract:
                    continue  # skip papers with no abstract — useless for synthesis

                article_ids = item.get("articleids", [])
                doi = next((a.get("value", "") for a in article_ids if a.get("idtype") == "doi"), "")
                authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]

                papers.append({
                    "title": item["title"].strip(),
                    "authors": authors,
                    "authors_str": ", ".join(authors[:3]) if authors else "Unknown Author",
                    "abstract": abstract,
                    "published": item.get("epubdate") or item.get("pubdate") or "",
                    "pdf_url": "",
                    "entry_id": f"pubmed:{pmid}",
                    "categories": ["PubMed"],
                    "primary_category": "pubmed",
                    "query_used": search_query,
                    "retrieved_at": datetime.now().isoformat(),
                    "source": "pubmed",
                    "doi": doi,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "citations": 0,
                })
                if len(papers) >= max_results:
                    break
        except Exception as e:
            print(f"   [!] PubMed retrieval failed: {e}")
        return papers

    def _fetch_pubmed_abstracts(self, pmids: List[str]) -> Dict[str, str]:
        """Fetch abstracts for PMIDs via NCBI efetch."""
        if not pmids:
            return {}
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        params_tool = "tool=researchgen&email=researchgen@example.com"
        url = f"{base}/efetch.fcgi?db=pubmed&id={','.join(pmids)}&retmode=xml&rettype=abstract&{params_tool}"
        out: Dict[str, str] = {}
        try:
            resp = self._session.get(url, timeout=self.http_timeout)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            for article in root.findall(".//PubmedArticle"):
                pmid_elem = article.find(".//PMID")
                if pmid_elem is None or not pmid_elem.text:
                    continue
                pmid = pmid_elem.text.strip()
                abstract_texts = article.findall(".//AbstractText")
                if abstract_texts:
                    parts = []
                    for at in abstract_texts:
                        label = at.get("Label", "")
                        text = (at.text or "").strip()
                        if label and text:
                            parts.append(f"{label}: {text}")
                        elif text:
                            parts.append(text)
                    out[pmid] = " ".join(parts)
        except Exception:
            pass
        return out

    # ------------------------------------------------------------------
    # CrossRef (cross-discipline metadata + reference lists)
    # ------------------------------------------------------------------

    def _retrieve_crossref(
        self,
        keywords: List[str],
        max_results: int,
        synonyms: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict]:
        """Search CrossRef. Uniquely exposes reference lists used to wire the
        Citation Graph (other sources rarely return references)."""
        query = " ".join([k for k in keywords if k and k.strip()][:6])
        if not query:
            return []
        url = "https://api.crossref.org/works"
        params: Dict[str, Any] = {
            "query.bibliographic": query,
            "rows": min(max_results * 2, 40),
            "select": "DOI,title,author,abstract,issued,container-title,"
                      "is-referenced-by-count,URL,reference",
            "sort": "relevance",
        }
        if self.crossref_mailto:
            params["mailto"] = self.crossref_mailto

        papers: List[Dict] = []
        try:
            resp = self._session.get(url, params=params, timeout=self.http_timeout)
            resp.raise_for_status()
            items = (resp.json().get("message") or {}).get("items", [])
            for item in items:
                title_list = item.get("title") or []
                title = (title_list[0] if title_list else "").strip()
                if not title:
                    continue

                authors = []
                for auth in item.get("author", [])[:6]:
                    name = " ".join(
                        p for p in [auth.get("given", ""), auth.get("family", "")] if p
                    ).strip()
                    if name:
                        authors.append(name)

                issued = (item.get("issued") or {}).get("date-parts") or [[None]]
                year = issued[0][0] if issued and issued[0] else None
                published = f"{year}-01-01" if year else ""

                container = item.get("container-title") or []
                venue = container[0] if container else "crossref"

                # Reference list (DOIs) → consumed by CitationGraph
                references = [
                    {"DOI": ref.get("DOI")}
                    for ref in (item.get("reference") or [])
                    if isinstance(ref, dict) and ref.get("DOI")
                ]

                abstract = item.get("abstract") or ""
                # CrossRef abstracts are JATS XML; strip tags for plain text
                if abstract:
                    abstract = re.sub(r"<[^>]+>", " ", abstract).strip()

                papers.append({
                    "title": title,
                    "authors": authors,
                    "authors_str": ", ".join(authors[:3]) if authors else "Unknown Author",
                    "abstract": abstract,
                    "published": published,
                    "pdf_url": "",
                    "entry_id": item.get("DOI", ""),
                    "categories": [venue],
                    "primary_category": venue,
                    "query_used": query,
                    "retrieved_at": datetime.now().isoformat(),
                    "source": "crossref",
                    "doi": item.get("DOI", ""),
                    "url": item.get("URL", ""),
                    "citations": item.get("is-referenced-by-count", 0) or 0,
                    "references": references,
                })
                if len(papers) >= max_results:
                    break
        except Exception as e:
            print(f"   [!] CrossRef retrieval failed: {e}")
        return papers

    # ------------------------------------------------------------------
    # Semantic helpers (optional — degrade gracefully without embeddings)
    # ------------------------------------------------------------------

    def _fuzzy_dedup(self, papers: List[Dict], threshold: int = 90) -> List[Dict]:
        """Merge papers whose titles are >threshold% similar (rapidfuzz
        token_sort_ratio), keeping the more-cited copy. No-op if rapidfuzz
        is unavailable or the list is trivially small."""
        if len(papers) < 2:
            return papers
        try:
            from rapidfuzz import fuzz
        except Exception:
            return papers

        def _norm(t: str) -> str:
            # lowercase + strip punctuation (so "Smart-Grid" == "Smart Grid")
            return re.sub(r"\s{2,}", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()

        kept: List[Dict] = []
        kept_norm: List[str] = []
        for paper in papers:
            title = (paper.get("title") or "").strip()
            if not title:
                continue
            ntitle = _norm(title)
            dup_idx = -1
            for i, kn in enumerate(kept_norm):
                if fuzz.token_sort_ratio(ntitle, kn) >= threshold:
                    dup_idx = i
                    break
            if dup_idx == -1:
                kept.append(paper)
                kept_norm.append(ntitle)
            elif int(paper.get("citations", 0) or 0) > int(kept[dup_idx].get("citations", 0) or 0):
                kept[dup_idx] = paper  # keep the higher-impact duplicate
        return kept

    def _semantic_dedup(self, papers: List[Dict], threshold: float = 0.92) -> List[Dict]:
        """Merge near-duplicate papers whose titles are semantically ~identical
        (e.g. preprint vs published), keeping the more-cited copy."""
        if not self.use_semantic or len(papers) < 2:
            return papers
        model = _get_embed_model()
        if model is None:
            return papers
        try:
            from sentence_transformers import util as _st_util
            titles = [p.get("title", "") for p in papers]
            emb = model.encode(titles, convert_to_tensor=True, normalize_embeddings=True)
            sim = _st_util.cos_sim(emb, emb)
            kept: List[int] = []
            dropped: Set[int] = set()
            for i in range(len(papers)):
                if i in dropped:
                    continue
                kept.append(i)
                for j in range(i + 1, len(papers)):
                    if j in dropped:
                        continue
                    if float(sim[i][j]) >= threshold:
                        # keep whichever has more citations; drop the other
                        if papers[j].get("citations", 0) > papers[i].get("citations", 0):
                            dropped.add(i)
                            kept[-1] = j
                        else:
                            dropped.add(j)
            return [papers[i] for i in sorted(set(kept) - dropped)]
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Semantic dedup skipped: {exc}")
            return papers

    def _semantic_relevance(self, papers: List[Dict], query_text: str) -> None:
        """Blend a semantic similarity signal into each paper's relevance_score
        (in place). No-op if embeddings are unavailable."""
        if not self.use_semantic or not papers:
            return
        model = _get_embed_model()
        if model is None:
            return
        try:
            from sentence_transformers import util as _st_util
            docs = [f"{p.get('title', '')}. {p.get('abstract', '')}"[:512] for p in papers]
            q_emb = model.encode([query_text], convert_to_tensor=True, normalize_embeddings=True)
            d_emb = model.encode(docs, convert_to_tensor=True, normalize_embeddings=True)
            sims = _st_util.cos_sim(q_emb, d_emb)[0]
            for paper, sim in zip(papers, sims):
                lexical = float(paper.get("relevance_score", 0.0))
                semantic = max(0.0, float(sim))
                # 60% lexical / 40% semantic blend
                paper["relevance_score"] = round(0.6 * lexical + 0.4 * semantic, 4)
                paper["semantic_score"] = round(semantic, 4)
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Semantic relevance skipped: {exc}")

    # ------------------------------------------------------------------
    # Citation Graph
    # ------------------------------------------------------------------

    def build_citation_graph(self, papers: List[Dict]) -> Dict[str, Any]:
        """Build the shared Citation Graph from retrieved papers."""
        return CitationGraph.from_papers(papers).to_dict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve_papers(
        self,
        keywords: List[str],
        max_results: int = 5,
        sources: Optional[List[str]] = None,
        topic: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve papers with domain-based routing, source status tracking,
        cross-source deduplication, and citation-aware ranking.

        Args:
            keywords: List of keywords (used directly if *topic* is None).
            max_results: Target number of papers after filtering.
            sources: Explicit list of source names. If None, auto-routed by domain.
            topic: Optional raw research topic for keyword-agent enrichment.
            domain: Force a domain ('health', 'cs', 'general'). If None, auto-detected.

        Returns:
            Dict with 'papers', 'domain', 'source_status', and optional 'warnings'.
        """
        start_time = datetime.now().timestamp()

        # --- Keyword enrichment ---
        synonyms: Optional[Dict[str, List[str]]] = None
        if topic and self.keyword_agent is not None:
            enriched = self.enrich_keywords_from_topic(topic, top_n=max(8, max_results + 3))
            if enriched.get("keywords"):
                keywords = enriched["keywords"]
                synonyms = enriched.get("synonyms")
                print(f"   [>>] Keyword agent enriched query: {keywords}")

        # Guard: if we still have no keywords, we cannot search meaningfully
        keywords = [k for k in keywords if k and k.strip()]
        if not keywords:
            print("   [!] No valid keywords provided and no topic to extract from; returning empty results")
            return {"papers": [], "domain": domain or "general", "source_status": {}, "total": 0}

        # --- Domain classification ---
        query_text = " ".join(keywords)
        resolved_domain = (domain or "auto").lower()
        if resolved_domain == "auto":
            resolved_domain = _classify_domain(query_text)
        print(f"   [>>] Domain classified as: {resolved_domain}")

        # --- Determine active sources based on domain ---
        if sources:
            active_sources = [s.lower() for s in sources]
        elif resolved_domain == "health":
            active_sources = ["pubmed", "semantic_scholar", "crossref"]
        elif resolved_domain == "cs":
            active_sources = ["arxiv", "semantic_scholar", "crossref"]
        else:
            active_sources = ["arxiv", "pubmed", "openalex", "semantic_scholar", "crossref"]

        # --- Cache lookup ---
        cache_key = self._make_cache_key(keywords + [resolved_domain], max_results, active_sources)
        cached = retrieval_cache.get(cache_key)
        if cached is not None:
            elapsed = int((datetime.now().timestamp() - start_time) * 1000)
            print(f"   [OK] Retrieval cache hit in {elapsed}ms")
            return cached

        provider_fetchers = {
            "arxiv": self._retrieve_arxiv,
            "openalex": self._retrieve_openalex,
            "semantic_scholar": self._retrieve_semantic_scholar,
            "pubmed": self._retrieve_pubmed,
            "crossref": self._retrieve_crossref,
        }

        # --- Source status tracker ---
        source_status: Dict[str, str] = {}

        def _safe_fetch(source: str, fetcher, limit: int) -> List[Dict]:
            try:
                results = fetcher(keywords, limit, synonyms)
                source_status[source] = "ok" if results else "empty"
                return results
            except Exception as exc:
                source_status[source] = "error"
                print(f"   [!] {source} fetch failed: {exc}")
                return []

        # --- Parallel fetch with domain-aware allocation ---
        all_candidates: List[Dict] = []

        with ThreadPoolExecutor(max_workers=len(active_sources)) as executor:
            futures: Dict[Any, Tuple[str, int]] = {}
            for source in active_sources:
                fetcher = provider_fetchers.get(source)
                if not fetcher:
                    continue
                # Domain-aware result allocation
                if resolved_domain == "health":
                    limit = max_results if source == "pubmed" else max_results // 2
                elif resolved_domain == "cs":
                    limit = max_results if source == "arxiv" else max_results // 2
                else:
                    limit = max_results if source in ("arxiv", "pubmed") else max_results // 2
                limit = max(limit, 3)
                future = executor.submit(_safe_fetch, source, fetcher, limit)
                futures[future] = (source, limit)

            for future in as_completed(futures):
                results = future.result()
                all_candidates.extend(results)

        # --- Cross-source deduplication by URL and DOI ---
        seen_urls: Set[str] = set()
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_candidates: List[Dict] = []

        for paper in all_candidates:
            url = (paper.get("url") or "").strip()
            doi = (paper.get("doi") or "").strip()
            title_key = (paper.get("title") or "").strip().lower()

            if not title_key:
                continue
            if title_key in seen_titles:
                continue
            if url and url in seen_urls:
                continue
            if doi and doi in seen_dois:
                continue

            seen_titles.add(title_key)
            if url:
                seen_urls.add(url)
            if doi:
                seen_dois.add(doi)
            unique_candidates.append(paper)

        # --- Fuzzy title dedup (rapidfuzz >90%) then semantic near-dup merge ---
        unique_candidates = self._fuzzy_dedup(unique_candidates)
        unique_candidates = self._semantic_dedup(unique_candidates)

        # --- Lexical score + recency filter ---
        scored: List[Dict] = []
        for paper in unique_candidates:
            paper["relevance_score"] = self.calculate_relevance_score(paper, keywords)
            if paper.get("published") and not self.is_recent_paper(paper["published"]):
                continue
            scored.append(paper)

        # --- Blend in semantic relevance (in place), then quality filter ---
        self._semantic_relevance(scored, query_text)
        papers = [p for p in scored if float(p.get("relevance_score", 0)) >= self.min_relevance_score]

        # Sort by relevance descending, then citations descending
        papers.sort(
            key=lambda p: (float(p.get("relevance_score", 0)), int(p.get("citations", 0))),
            reverse=True,
        )
        papers = papers[:max_results]

        # --- Attach per-paper provenance (traceability) ---
        for paper in papers:
            paper["provenance"] = {
                "source": paper.get("source", ""),
                "query_used": paper.get("query_used", query_text),
                "retrieved_at": paper.get("retrieved_at", ""),
                "doi": paper.get("doi", ""),
                "url": paper.get("url", ""),
            }

        elapsed = int((datetime.now().timestamp() - start_time) * 1000)
        print(f"   [OK] Retrieval complete: {len(papers)} papers in {elapsed}ms")

        # --- Build warnings ---
        warnings: List[str] = []
        expected = {
            "health": ["pubmed", "semantic_scholar", "crossref"],
            "cs": ["arxiv", "semantic_scholar", "crossref"],
            "general": ["arxiv", "pubmed", "openalex", "semantic_scholar", "crossref"],
        }.get(resolved_domain, active_sources)
        for src in expected:
            status = source_status.get(src, "skipped")
            if status == "empty":
                warnings.append(f"{src}: returned 0 results")
            elif status == "error":
                warnings.append(f"{src}: request failed")

        result = {
            "papers": papers,
            "domain": resolved_domain,
            "source_status": source_status,
            "total": len(papers),
            "query": query_text,
            "citation_graph": self.build_citation_graph(papers),
        }
        if warnings:
            result["warnings"] = warnings

        # Cache result
        retrieval_cache.set(cache_key, result)
        return result

    def retrieve_papers_multi_query(
        self,
        keywords: List[str],
        subtopics: Dict[str, List[str]],
        max_results: int = 5,
        topic: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Advanced retrieval using main keywords + subtopic variations.
        Delegates to retrieve_papers with an expanded keyword set.
        """
        expanded_keywords = list(keywords)
        for main_kw, related in subtopics.items():
            for r in related[:2]:
                if r not in expanded_keywords:
                    expanded_keywords.append(r)

        return self.retrieve_papers(
            keywords=expanded_keywords,
            max_results=max_results,
            topic=topic,
            domain=domain,
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _merge_dedupe_rank(
        self, candidates: List[Dict], keywords: List[str], max_results: int
    ) -> List[Dict]:
        """Shared post-processing: exact + fuzzy + semantic dedup, score, recency
        filter, semantic-relevance blend, rank, provenance."""
        seen_urls: Set[str] = set()
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        unique: List[Dict] = []
        for paper in candidates:
            url = (paper.get("url") or "").strip()
            doi = (paper.get("doi") or "").strip()
            tkey = (paper.get("title") or "").strip().lower()
            if not tkey or tkey in seen_titles:
                continue
            if url and url in seen_urls:
                continue
            if doi and doi in seen_dois:
                continue
            seen_titles.add(tkey)
            if url:
                seen_urls.add(url)
            if doi:
                seen_dois.add(doi)
            unique.append(paper)

        unique = self._fuzzy_dedup(unique)
        unique = self._semantic_dedup(unique)

        query_text = " ".join(keywords)
        scored: List[Dict] = []
        for paper in unique:
            paper["relevance_score"] = self.calculate_relevance_score(paper, keywords)
            if paper.get("published") and not self.is_recent_paper(paper["published"]):
                continue
            scored.append(paper)

        self._semantic_relevance(scored, query_text)
        papers = [p for p in scored if float(p.get("relevance_score", 0)) >= self.min_relevance_score]
        papers.sort(
            key=lambda p: (float(p.get("relevance_score", 0)), int(p.get("citations", 0))),
            reverse=True,
        )
        papers = papers[:max_results]
        for paper in papers:
            paper.setdefault("provenance", {
                "source": paper.get("source", ""),
                "query_used": paper.get("query_used", query_text),
                "retrieved_at": paper.get("retrieved_at", ""),
                "doi": paper.get("doi", ""),
                "url": paper.get("url", ""),
            })
        return papers

    def retrieve_with_boolean_queries(
        self,
        queries: List[str],
        keywords: List[str],
        max_results: int = 8,
    ) -> Dict[str, Any]:
        """Execute boolean query strings concurrently — arXiv (native boolean)
        + Semantic Scholar / CrossRef (operator-stripped keyword form) — then
        merge/dedupe/rank into a single ranked corpus + citation graph."""
        from backend.core_agents.query_builder import strip_boolean

        cap = int(os.getenv("SEARCH_MAX_BOOL_QUERIES", "8"))
        queries = [q for q in (queries or []) if q and q.strip()][:cap]
        if not queries:
            return {
                "papers": [], "domain": "boolean", "source_status": {}, "total": 0,
                "citation_graph": self.build_citation_graph([]), "boolean_queries_used": [],
            }

        per_q = max(3, max_results // 2)
        source_status: Dict[str, str] = {}

        def _run(q: str) -> List[Dict]:
            out: List[Dict] = []
            plain = strip_boolean(q)
            try:
                out.extend(self._retrieve_arxiv([], per_q, raw_query=q))
                source_status["arxiv"] = "ok"
            except Exception:
                source_status.setdefault("arxiv", "error")
            try:
                out.extend(self._retrieve_semantic_scholar([], per_q, raw_query=plain))
                source_status["semantic_scholar"] = "ok"
            except Exception:
                source_status.setdefault("semantic_scholar", "error")
            try:
                out.extend(self._retrieve_crossref([plain], per_q))
                source_status["crossref"] = "ok"
            except Exception:
                source_status.setdefault("crossref", "error")
            return out

        all_candidates: List[Dict] = []
        with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
            for res in executor.map(_run, queries):
                all_candidates.extend(res)

        papers = self._merge_dedupe_rank(all_candidates, keywords, max_results)
        return {
            "papers": papers,
            "domain": "boolean",
            "source_status": source_status,
            "total": len(papers),
            "query": "; ".join(queries[:3]),
            "citation_graph": self.build_citation_graph(papers),
            "boolean_queries_used": queries,
        }

    def retrieve_models(self, keywords: List[str], max_results: int = 8, **kwargs):
        """Typed accessor: return the ranked corpus as a Pydantic ``RankedCorpus``."""
        from backend.core_agents.schemas import RankedCorpus
        return RankedCorpus.from_result(
            self.retrieve_papers(keywords, max_results=max_results, **kwargs)
        )

    @staticmethod
    def _make_cache_key(keywords: List[str], max_results: int, sources: Optional[List[str]]) -> str:
        payload = "|".join(sorted(k.lower().strip() for k in keywords))
        src = ",".join(sorted(sources or []))
        return hashlib.sha256(f"{payload}:{max_results}:{src}".encode()).hexdigest()[:32]


# Backwards-compatible alias (legacy imports expect ``PaperRetrievalAgent``).
PaperRetrievalAgent = SearchAgent


# Test function
if __name__ == "__main__":
    agent = SearchAgent(min_relevance_score=0.5, min_year=2020)
    test_keywords = ["language models", "healthcare", "clinical applications"]

    print("Testing Paper Retrieval (parallel, cached)...")
    result = agent.retrieve_papers(test_keywords, max_results=3)
    papers = result.get("papers", [])

    print(f"\nDomain: {result.get('domain')}")
    print(f"Source status: {result.get('source_status')}")
    if result.get("warnings"):
        print(f"Warnings: {result['warnings']}")
    print(f"\nRetrieved {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Authors: {paper['authors_str']}")
        print(f"   Published: {paper['published']}")
        print(f"   Relevance Score: {paper['relevance_score']:.1%}")
        print(f"   Citations: {paper.get('citations', 0)}")
        print(f"   Source: {paper['source']}")
        print(f"   Abstract: {paper['abstract'][:150]}...")
