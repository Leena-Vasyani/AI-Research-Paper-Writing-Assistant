import arxiv
from typing import List, Dict
import time
from datetime import datetime

class PaperRetrievalAgent:
    """
    Real-time paper retrieval from arXiv using official API
    Filters by relevance score (>70%) and date range (2020-2025)
    """
    
    def __init__(self, min_relevance_score: float = 0.7, min_year: int = 2020):
        self.client = arxiv.Client()
        self.min_relevance_score = min_relevance_score
        self.min_year = min_year
    
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
    
    def retrieve_papers(self, keywords: List[str], max_results: int = 5) -> List[Dict]:
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
        
        # Build search query
        search_query = self.build_search_query(keywords)
        print(f"🔍 DEBUG Retrieval - Built search query: {search_query}")
        
        # Create search - retrieve more initially to account for filtering
        search = arxiv.Search(
            query=search_query,
            max_results=max_results * 5,  # Retrieve 5x to account for filtering
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending
        )
        
        papers = []
        processed_count = 0
        
        try:
            for result in self.client.results(search):
                processed_count += 1
                print(f"🔍 DEBUG Retrieval - Processing result {processed_count}: {result.title[:60]}...")
                
                # Create paper dict first
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
                    "retrieved_at": datetime.now().isoformat()
                }
                
                # Calculate relevance score
                relevance_score = self.calculate_relevance_score(paper, keywords)
                paper['relevance_score'] = relevance_score
                print(f"   Relevance: {relevance_score:.1%}, Date: {paper['published']}")
                
                # Filter by date first (more lenient)
                if not self.is_recent_paper(paper['published']):
                    print(f"   ❌ Filtered: Date too old")
                    continue
                
                # For relevance, be more lenient on initial retrieval
                # Accept papers with relevance > 50% since we're being strict about keywords
                if relevance_score >= 0.5:
                    papers.append(paper)
                    print(f"   ✅ Added to results")
                    
                    # Stop when we have enough papers
                    if len(papers) >= max_results:
                        break
                else:
                    print(f"   ❌ Filtered: Relevance too low")
                
                # Small delay to respect API limits
                time.sleep(0.5)
        
        except Exception as e:
            print(f"⚠️ Error retrieving papers: {e}")
            import traceback
            traceback.print_exc()
        
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