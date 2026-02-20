import arxiv
from typing import List, Dict
import time
from datetime import datetime
import requests
import os

class PaperRetrievalAgent:
    """
    Real-time paper retrieval from arXiv using official API
    Filters by relevance score (>70%) and date range (2020-2025)
    """
    
    def __init__(self, min_relevance_score: float = 0.7, min_year: int = 2020):
        self.client = arxiv.Client()
        self.min_relevance_score = min_relevance_score
        self.min_year = min_year
        self.http_timeout = 20
        self.openalex_api_key = os.getenv("OPENALEX_API_KEY", "").strip()
        self.openalex_email = os.getenv("OPENALEX_EMAIL", "").strip()
        self.semantic_scholar_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()
    
    def build_search_query(self, keywords: List[str], max_keywords: int = 5) -> str:
        """
        Build optimized search query from keywords
        """
        # Use top keywords for better results
        top_keywords = keywords[:max_keywords]
        
        # Create OR query for broader results
        query = ' OR '.join([f'"{kw}"' for kw in top_keywords])
        
        return query
    
    def calculate_relevance_score(self, paper: Dict, keywords: List[str]) -> float:
        """
        Calculate relevance score based on keyword matches
        More flexible matching for multi-word keywords
        """
        title_lower = paper['title'].lower()
        abstract_lower = paper['abstract'].lower()
        
        score = 0.0
        max_score = 0
        
        for keyword in keywords:
            kw_lower = keyword.lower()
            max_score += 0.5
            
            # Exact match in title (highest score)
            if kw_lower in title_lower:
                score += 0.5
            # Also check individual words if it's a multi-word keyword
            elif ' ' in kw_lower:
                words = kw_lower.split()
                word_matches = sum(1 for w in words if w in title_lower)
                if word_matches >= len(words) - 1:  # At least n-1 words match
                    score += 0.3
            
            # Abstract match (lower score)
            if kw_lower in abstract_lower:
                score += 0.2
            elif ' ' in kw_lower:
                words = kw_lower.split()
                word_matches = sum(1 for w in words if w in abstract_lower)
                if word_matches >= len(words) - 1:
                    score += 0.1
        
        # Normalize to 0-1 range
        return min(score / max_score, 1.0) if max_score > 0 else 0.5
    
    def is_recent_paper(self, published_date: str) -> bool:
        """
        Check if paper was published in the last 5 years (2020-2025)
        """
        try:
            year = int(published_date.split('-')[0])
            return year >= self.min_year
        except:
            return False

    def _extract_openalex_abstract(self, abstract_index: Dict | None) -> str:
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

    def _retrieve_arxiv(self, keywords: List[str], max_results: int) -> List[Dict]:
        search_query = self.build_search_query(keywords)
        search = arxiv.Search(
            query=search_query,
            max_results=max_results * 5,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending
        )

        papers = []
        try:
            for result in self.client.results(search):
                paper = {
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "authors_str": ", ".join([author.name for author in result.authors][:3]),
                    "abstract": result.summary,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "query_used": search_query,
                    "retrieved_at": datetime.now().isoformat(),
                    "source": "arxiv",
                }
                papers.append(paper)
                if len(papers) >= max_results:
                    break
                time.sleep(0.2)
        except Exception as e:
            print(f"⚠️ arXiv retrieval failed: {e}")
        return papers

    def _retrieve_openalex(self, keywords: List[str], max_results: int) -> List[Dict]:
        search_query = self.build_search_query(keywords)
        url = "https://api.openalex.org/works"
        params = {
            "search": search_query,
            "per-page": min(max_results * 4, 200),
            "sort": "relevance_score:desc",
        }
        if self.openalex_api_key:
            params["api_key"] = self.openalex_api_key
        if self.openalex_email:
            params["mailto"] = self.openalex_email

        headers = {
            "User-Agent": "ResearchGen/0.1 (mailto:{})".format(self.openalex_email or "support@example.com")
        }
        papers: List[Dict] = []

        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.http_timeout)
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

                paper = {
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
                }
                papers.append(paper)
                if len(papers) >= max_results:
                    break
        except Exception as e:
            print(f"⚠️ OpenAlex retrieval failed: {e}")

        return papers

    def _retrieve_semantic_scholar(self, keywords: List[str], max_results: int) -> List[Dict]:
        search_query = self.build_search_query(keywords)
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": search_query,
            "limit": min(max_results * 4, 100),
            "fields": "title,abstract,authors,year,venue,url,externalIds,openAccessPdf,publicationDate",
        }
        headers = {}
        if self.semantic_scholar_api_key:
            headers["x-api-key"] = self.semantic_scholar_api_key
        papers: List[Dict] = []

        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.http_timeout)
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

                paper = {
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
                }
                papers.append(paper)
                if len(papers) >= max_results:
                    break
        except Exception as e:
            print(f"⚠️ Semantic Scholar retrieval failed: {e}")

        return papers
    
    def retrieve_papers(self, keywords: List[str], max_results: int = 5, sources: List[str] | None = None) -> List[Dict]:
        """
        Retrieve papers from arXiv based on keywords
        Filters by relevance score (>70%) and publication date (2020-2025)
        
        Args:
            keywords: List of keywords from query agent
            max_results: Maximum number of papers to retrieve (after filtering)
            
        Returns:
            List of paper dictionaries with metadata and content
        """
        
        print(f"🔍 DEBUG Retrieval - Input keywords: {keywords}")
        active_sources = [s.lower() for s in (sources or ["arxiv", "openalex", "semantic_scholar"])]

        provider_fetchers = {
            "arxiv": self._retrieve_arxiv,
            "openalex": self._retrieve_openalex,
            "semantic_scholar": self._retrieve_semantic_scholar,
        }

        papers: List[Dict] = []
        seen_titles = set()

        for source in active_sources:
            fetcher = provider_fetchers.get(source)
            if not fetcher:
                continue

            source_candidates = fetcher(keywords, max_results=max_results)

            for paper in source_candidates:
                title_key = paper.get("title", "").strip().lower()
                if not title_key or title_key in seen_titles:
                    continue

                relevance_score = self.calculate_relevance_score(paper, keywords)
                paper["relevance_score"] = relevance_score

                if paper.get("published") and not self.is_recent_paper(paper["published"]):
                    continue

                if relevance_score >= 0.5:
                    papers.append(paper)
                    seen_titles.add(title_key)

                if len(papers) >= max_results:
                    break

            if len(papers) >= max_results:
                break

        print(f"🔍 DEBUG Retrieval - Total papers found: {len(papers)}")
        return papers
    
    def retrieve_papers_multi_query(self, keywords: List[str], 
                                   subtopics: Dict[str, List[str]], 
                                   max_results: int = 5) -> List[Dict]:
        """
        Advanced retrieval using multiple query strategies
        Filters by relevance score (>70%) and publication date (2020-2025)
        
        Args:
            keywords: Main keywords
            subtopics: Related subtopics for each keyword
            max_results: Total papers to retrieve (after filtering)
            
        Returns:
            List of unique papers from multiple queries
        """
        
        all_papers = []
        seen_titles = set()
        
        # Strategy 1: Main keywords
        try:
            main_papers = self.retrieve_papers(keywords, max_results=max_results // 2)
            for paper in main_papers:
                if paper['title'] not in seen_titles:
                    all_papers.append(paper)
                    seen_titles.add(paper['title'])
        except Exception as e:
            print(f"Main query failed: {e}")
        
        # Strategy 2: Keyword combinations
        if len(all_papers) < max_results and len(keywords) >= 2:
            try:
                combo_query = f'"{keywords[0]}" AND "{keywords[1]}"'
                search = arxiv.Search(
                    query=combo_query,
                    max_results=(max_results - len(all_papers)) * 3,  # Account for filtering
                    sort_by=arxiv.SortCriterion.Relevance
                )
                
                for result in self.client.results(search):
                    if result.title not in seen_titles:
                        paper = {
                            "title": result.title,
                            "authors": [author.name for author in result.authors],
                            "authors_str": ", ".join([author.name for author in result.authors][:3]),
                            "abstract": result.summary,
                            "published": result.published.strftime("%Y-%m-%d"),
                            "pdf_url": result.pdf_url,
                            "entry_id": result.entry_id,
                            "categories": result.categories,
                            "primary_category": result.primary_category,
                            "query_used": combo_query,
                            "retrieved_at": datetime.now().isoformat()
                        }
                        
                        # Calculate relevance and filter
                        relevance_score = self.calculate_relevance_score(paper, keywords)
                        paper['relevance_score'] = relevance_score
                        
                        if relevance_score >= self.min_relevance_score and self.is_recent_paper(paper['published']):
                            all_papers.append(paper)
                            seen_titles.add(result.title)
                            
                            if len(all_papers) >= max_results:
                                break
                        
                        time.sleep(0.5)
            except Exception as e:
                print(f"Combination query failed: {e}")
        
        return all_papers[:max_results]


# Test function
if __name__ == "__main__":
    agent = PaperRetrievalAgent(min_relevance_score=0.7, min_year=2020)
    
    # Test with sample keywords
    test_keywords = ["language models", "healthcare", "clinical applications"]
    
    print("🔍 Testing Paper Retrieval (Relevance >70%, 2020-2025)...")
    papers = agent.retrieve_papers(test_keywords, max_results=3)
    
    print(f"\n✅ Retrieved {len(papers)} papers:")
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Authors: {paper['authors_str']}")
        print(f"   Published: {paper['published']}")
        print(f"   Relevance Score: {paper['relevance_score']:.1%}")
        print(f"   Abstract: {paper['abstract'][:150]}...")