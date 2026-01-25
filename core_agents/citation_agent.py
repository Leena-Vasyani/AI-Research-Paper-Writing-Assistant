import re
import json
from typing import Dict, List, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import string
from datetime import datetime

class CitationAgent:
    """
    Intelligent citation agent that:
    1. Analyzes generated draft text
    2. Identifies where citations are needed
    3. Matches with relevant retrieved papers
    4. Adds proper academic citations in appropriate formats
    """
    
    def __init__(self):
        self.citation_styles = {
            "apa": {
                "in_text": "({author}, {year})",
                "reference": "{author_last}, {author_first_initial}. ({year}). {title}. {journal}. {doi}"
            },
            "ieee": {
                "in_text": "[{number}]",
                "reference": "[{number}] {author_last}, {author_first_initial}. \"{title},\" {journal}, {year}."
            },
            "mla": {
                "in_text": "({author_last} {page})",
                "reference": "{author_last}, {author_first}. \"{title}.\" {journal}, {year}, {pages}."
            }
        }
        
    def extract_citation_needs(self, draft_text: str) -> List[Tuple[str, int]]:
        """
        Identify sentences/claims that need citations
        
        Returns:
            List of (sentence, position) tuples where citations are needed
        """
        citation_patterns = [
            # Patterns that typically need citations
            r'[^.]* (?:shows?|demonstrates?|proves?|confirms?|validates?|finds?|discovers?) that[^.]*\.',
            r'[^.]* (?:according to|as per|based on|following) [^.]*\.',
            r'[^.]* (?:reported by|described by|noted by) [^.]*\.',
            r'[^.]* (?:previous|prior|existing) (?:work|research|studies)[^.]*\.',
            r'[^.]* (?:literature|studies|research) (?:suggests|indicates|shows)[^.]*\.',
            r'[^.]* (?:similar|comparable) (?:results|findings)[^.]*\.',
            r'[^.]* (?:in contrast|however|on the other hand)[^.]*\.',
            r'[^.]* (?:standard|commonly used|typical) (?:approach|method)[^.]*\.',
        ]
        
        sentences = re.split(r'[.!?]+', draft_text)
        citation_needs = []
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence.split()) > 5:  # Meaningful sentence
                for pattern in citation_patterns:
                    if re.search(pattern, sentence.lower()):
                        # Calculate position in original text
                        position = draft_text.find(sentence)
                        if position != -1:
                            citation_needs.append((sentence, position))
                        break
        
        return citation_needs
    
    def find_relevant_citations(self, citation_sentence: str, retrieved_papers: List[Dict]) -> List[Dict]:
        """
        Find relevant papers to cite for a given sentence
        
        Returns:
            List of relevant paper dictionaries with relevance scores
        """
        relevant_papers = []
        
        # Extract key terms from the sentence
        sentence_terms = self._extract_key_terms(citation_sentence)
        
        for paper in retrieved_papers:
            relevance_score = self._calculate_citation_relevance(
                citation_sentence, 
                sentence_terms,
                paper
            )
            
            if relevance_score > 0.3:  # Threshold for relevance
                relevant_papers.append({
                    "paper": paper,
                    "relevance_score": relevance_score,
                    "citation_type": self._determine_citation_type(citation_sentence, paper)
                })
        
        # Sort by relevance
        relevant_papers.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_papers[:3]  # Return top 3 most relevant
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for matching"""
        # Remove punctuation and lowercase
        text = text.lower().translate(str.maketrans('', '', string.punctuation))
        
        # Remove stop words and keep meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall'}
        
        words = text.split()
        key_terms = [word for word in words if word not in stop_words and len(word) > 3]
        
        return key_terms
    
    def _calculate_citation_relevance(self, sentence: str, sentence_terms: List[str], paper: Dict) -> float:
        """Calculate relevance between sentence and paper"""
        score = 0.0
        
        # Check paper title
        title = paper.get('title', '').lower()
        title_score = sum(1 for term in sentence_terms if term in title) / max(len(sentence_terms), 1)
        score += title_score * 0.4
        
        # Check abstract - use better matching
        abstract = paper.get('abstract', '').lower()
        # Check how many terms appear in abstract
        matching_terms = sum(1 for term in sentence_terms if term in abstract)
        abstract_score = matching_terms / max(len(sentence_terms), 1)
        score += abstract_score * 0.3
        
        # Check relevance score from retrieval (if available)
        relevance = paper.get('relevance', 0.0)
        score += relevance * 0.2
        
        # Check recency (prefer newer papers)
        published = paper.get('published', '')
        if published:
            try:
                year = int(published[:4])
                current_year = datetime.now().year
                recency_score = 1.0 - min(1.0, (current_year - year) / 10)  # Papers older than 10 years get lower score
                score += recency_score * 0.1
            except:
                pass
        
        return min(score, 1.0)
    
    def _determine_citation_type(self, sentence: str, paper: Dict) -> str:
        """Determine what type of citation this should be"""
        sentence_lower = sentence.lower()
        paper_title = paper.get('title', '').lower()
        
        # Method citation
        if any(word in sentence_lower for word in ['method', 'approach', 'technique', 'algorithm', 'model', 'framework']):
            if any(word in paper_title for word in ['method', 'approach', 'technique', 'algorithm']):
                return "method"
        
        # Result citation
        if any(word in sentence_lower for word in ['result', 'finding', 'shows', 'demonstrates', 'found', 'achieved']):
            if any(word in paper_title for word in ['result', 'finding', 'shows', 'demonstrates']):
                return "result"
        
        # Review/survey citation
        if any(word in sentence_lower for word in ['review', 'survey', 'overview', 'literature']):
            if any(word in paper_title for word in ['review', 'survey', 'overview']):
                return "review"
        
        # General citation
        return "general"
    
    def format_citation(self, paper: Dict, citation_style: str = "apa", citation_number: int = None) -> Dict:
        """Format citation in specified style"""
        style = self.citation_styles.get(citation_style, self.citation_styles["apa"])
        
        # Extract author information
        authors_str = paper.get('authors_str', 'Unknown Author')
        authors = authors_str.split(',')
        
        if len(authors) > 0:
            first_author = authors[0].strip()
            # Simple author parsing
            if ' ' in first_author:
                author_parts = first_author.split(' ')
                author_last = author_parts[-1]
                author_first_initial = author_parts[0][0] + '.'
            else:
                author_last = first_author
                author_first_initial = first_author[0] + '.'
        else:
            author_last = "Unknown"
            author_first_initial = "A."
        
        # Extract year
        published = paper.get('published', '')
        year = published[:4] if published and len(published) >= 4 else 'n.d.'
        
        # Extract title
        title = paper.get('title', 'Unknown Title')
        
        # Format journal/source
        journal = paper.get('primary_category', 'arXiv').replace('.', '')
        
        # Get DOI/URL
        doi = paper.get('doi', '')
        if not doi:
            doi = paper.get('pdf_url', '')
        
        # Create formatted citations
        in_text_citation = style["in_text"].format(
            author=author_last,
            year=year,
            number=citation_number,
            author_last=author_last,
            page=""
        )
        
        reference_entry = style["reference"].format(
            author_last=author_last,
            author_first_initial=author_first_initial,
            author_first=author_first_initial.rstrip('.'),
            year=year,
            title=title,
            journal=journal,
            doi=doi,
            number=citation_number,
            pages=""
        )
        
        return {
            "in_text": in_text_citation,
            "reference": reference_entry,
            "paper_info": {
                "title": title,
                "authors": authors_str,
                "year": year,
                "source": journal,
                "url": doi
            }
        }
    
    def add_citations_to_draft(self, draft_sections: Dict[str, str], 
                              retrieved_papers: List[Dict],
                              plagiarism_results: Dict = None,
                              citation_style: str = "apa") -> Dict[str, str]:
        """
        Add citations to draft sections intelligently
        Wrapper that detects if plagiarism results are provided
        
        Returns:
            Dictionary with cited sections and references
        """
        # If plagiarism results provided, use the advanced method
        if plagiarism_results:
            return self.add_citations_to_draft_with_plagiarism(
                draft_sections, retrieved_papers, plagiarism_results, citation_style
            )
        
        # Otherwise use basic citation method
        print("\n📝 Adding Intelligent Citations...")
        print("-" * 50)
        
        cited_sections = {}
        all_references = []
        citation_map = {}  # Track which papers are cited where
        
        for section_name, section_text in draft_sections.items():
            print(f"  • Analyzing {section_name}...")
            
            # Identify where citations are needed
            citation_needs = self.extract_citation_needs(section_text)
            print(f"    Found {len(citation_needs)} potential citation points")
            
            cited_text = section_text
            added_citations = 0
            
            for sentence, position in citation_needs:
                # Find relevant papers to cite
                relevant_papers = self.find_relevant_citations(sentence, retrieved_papers)
                
                if relevant_papers:
                    # Format citations
                    citations = []
                    for i, rel_paper in enumerate(relevant_papers[:2]):  # Max 2 citations per claim
                        paper = rel_paper["paper"]
                        
                        # Check if already cited
                        paper_id = paper.get('id', paper.get('title', ''))
                        if paper_id not in citation_map:
                            citation_number = len(all_references) + 1
                            formatted_citation = self.format_citation(paper, citation_style, citation_number)
                            
                            citation_map[paper_id] = {
                                "citation_number": citation_number,
                                "formatted_citation": formatted_citation,
                                "cited_in": [section_name]
                            }
                            all_references.append(formatted_citation)
                        else:
                            citation_number = citation_map[paper_id]["citation_number"]
                            citation_map[paper_id]["cited_in"].append(section_name)
                            formatted_citation = citation_map[paper_id]["formatted_citation"]
                        
                        citations.append(formatted_citation["in_text"])
                    
                    if citations:
                        # Insert citation after the sentence
                        citation_text = ' ' + ' '.join(citations)
                        
                        # Find the sentence in the text and add citation
                        sentence_end = position + len(sentence)
                        if sentence_end < len(cited_text):
                            cited_text = cited_text[:sentence_end] + citation_text + cited_text[sentence_end:]
                            added_citations += 1
            
            cited_sections[section_name] = cited_text
            print(f"    Added {added_citations} citations")
        
        # Format references section
        references_section = self._format_references_section(all_references, citation_style)
        cited_sections["references"] = references_section
        
        print(f"\n✅ Total citations added: {len(all_references)}")
        print(f"📚 References included: {len(set(ref['paper_info']['title'] for ref in all_references))}")
        
        return {
            "cited_draft": cited_sections,
            "citations_added": len(all_references),
            "references": all_references,
            "citation_map": citation_map
        }
    
    def add_citations_to_draft_with_plagiarism(self, draft_sections: Dict[str, str], 
                                              retrieved_papers: List[Dict],
                                              plagiarism_results: Dict = None,
                                              citation_style: str = "apa") -> Dict[str, str]:
        """
        Add citations intelligently, prioritizing plagiarized sentences
        
        Args:
            draft_sections: Dictionary of draft sections
            retrieved_papers: List of retrieved papers with metadata
            plagiarism_results: Results from plagiarism detection with flagged sentences
            citation_style: Citation format (apa, ieee, mla)
        
        Returns:
            Dictionary with cited sections and references
        """
        print("\n📝 Adding Intelligent Citations (with Plagiarism Priority)...")
        print("-" * 60)
        
        cited_sections = {}
        all_references = []
        citation_map = {}
        flagged_sentences_cited = 0
        
        for section_name, section_text in draft_sections.items():
            if section_name == "references":
                cited_sections[section_name] = section_text
                continue
            
            print(f"\n  🎯 Processing {section_name}...")
            
            # Get plagiarism flags for this section if available
            section_plagiarism = {}
            if plagiarism_results and 'section_analysis' in plagiarism_results:
                section_data = plagiarism_results['section_analysis'].get(section_name, {})
                flagged = section_data.get('flagged_sentences', [])
                
                # Create mapping of sentences to their source papers
                for flag in flagged:
                    sentence = flag.get('sentence', '')
                    source = flag.get('source', '')
                    similarity = flag.get('similarity', 0)
                    section_plagiarism[sentence] = {
                        'source': source,
                        'similarity': similarity
                    }
            
            cited_text = section_text
            citation_count = 0
            
            # PRIORITY 1: Citation for flagged (plagiarized) sentences
            if section_plagiarism:
                print(f"    📌 Found {len(section_plagiarism)} flagged sentences to cite")
                
                for flagged_sentence, plagiarism_info in section_plagiarism.items():
                    # Find the best paper to cite (prefer the source paper mentioned)
                    source_title = plagiarism_info['source']
                    matching_papers = [p for p in retrieved_papers 
                                     if source_title.lower() in p.get('title', '').lower() or
                                        source_title.lower() in p.get('abstract', '').lower()]
                    
                    if not matching_papers:
                        # If exact match not found, find semantically similar papers
                        matching_papers = self.find_relevant_citations(flagged_sentence, retrieved_papers)
                    
                    if matching_papers:
                        # Get the most relevant paper
                        if isinstance(matching_papers[0], dict) and 'paper' in matching_papers[0]:
                            paper = matching_papers[0]['paper']
                        else:
                            paper = matching_papers[0]
                        
                        # Format citation
                        paper_id = paper.get('id', paper.get('title', ''))
                        
                        if paper_id not in citation_map:
                            citation_number = len(all_references) + 1
                            formatted_citation = self.format_citation(paper, citation_style, citation_number)
                            
                            citation_map[paper_id] = {
                                "citation_number": citation_number,
                                "formatted_citation": formatted_citation,
                                "cited_in": [section_name],
                                "citation_count": 1,
                                "plagiarism_priority": True
                            }
                            all_references.append(formatted_citation)
                        else:
                            citation_number = citation_map[paper_id]["citation_number"]
                            citation_map[paper_id]["cited_in"].append(section_name)
                            citation_map[paper_id]["citation_count"] += 1
                            formatted_citation = citation_map[paper_id]["formatted_citation"]
                        
                        # Insert citation into text
                        in_text = formatted_citation["in_text"]
                        if flagged_sentence in cited_text:
                            # Find the sentence and add citation after it
                            position = cited_text.find(flagged_sentence)
                            if position != -1:
                                end_pos = position + len(flagged_sentence)
                                # Add citation before the period if it exists
                                if end_pos < len(cited_text) and cited_text[end_pos] in '.!?':
                                    cited_text = cited_text[:end_pos] + f" {in_text}" + cited_text[end_pos:]
                                else:
                                    cited_text = cited_text[:end_pos] + f" {in_text}" + cited_text[end_pos:]
                                
                                citation_count += 1
                                flagged_sentences_cited += 1
                                print(f"    ✅ Cited flagged sentence (similarity: {plagiarism_info['similarity']:.1%})")
            
            # PRIORITY 2: Citation for other academic claims
            additional_citations = self.extract_citation_needs(section_text)
            if additional_citations:
                print(f"    📚 Found {len(additional_citations)} additional citation points")
                
                for sentence, position in additional_citations[:5]:  # Limit to 5 per section
                    # Skip if this sentence was already flagged for plagiarism
                    if section_plagiarism and any(
                        sent.lower() in sentence.lower() for sent in section_plagiarism.keys()
                    ):
                        continue
                    
                    # Find relevant papers
                    relevant = self.find_relevant_citations(sentence, retrieved_papers)
                    
                    if relevant:
                        paper = relevant[0]['paper']
                        paper_id = paper.get('id', paper.get('title', ''))
                        
                        if paper_id not in citation_map:
                            citation_number = len(all_references) + 1
                            formatted = self.format_citation(paper, citation_style, citation_number)
                            
                            citation_map[paper_id] = {
                                "citation_number": citation_number,
                                "formatted_citation": formatted,
                                "cited_in": [section_name],
                                "citation_count": 1,
                                "plagiarism_priority": False
                            }
                            all_references.append(formatted)
                        else:
                            citation_number = citation_map[paper_id]["citation_number"]
                            formatted = citation_map[paper_id]["formatted_citation"]
                        
                        in_text = formatted["in_text"]
                        if sentence in cited_text:
                            position = cited_text.find(sentence)
                            end_pos = position + len(sentence)
                            if end_pos < len(cited_text) and cited_text[end_pos] in '.!?':
                                cited_text = cited_text[:end_pos] + f" {in_text}" + cited_text[end_pos:]
                            else:
                                cited_text = cited_text[:end_pos] + f" {in_text}" + cited_text[end_pos:]
                            
                            citation_count += 1
            
            cited_sections[section_name] = cited_text
            print(f"    ➕ Added {citation_count} citations to {section_name}")
        
        # Format references section
        references_section = self._format_references_section(all_references, citation_style)
        cited_sections["references"] = references_section
        
        print(f"\n{'='*60}")
        print(f"✅ CITATION SUMMARY")
        print(f"{'='*60}")
        print(f"📌 Flagged sentences cited: {flagged_sentences_cited}")
        print(f"📚 Total citations added: {len(all_references)}")
        print(f"📄 Unique papers: {len(set(ref['paper_info']['title'] for ref in all_references))}")
        
        # Show which papers had plagiarism priority
        plagiarism_priority_papers = [
            (k, v) for k, v in citation_map.items() 
            if v.get('plagiarism_priority', False)
        ]
        if plagiarism_priority_papers:
            print(f"⚠️  Papers cited for plagiarism: {len(plagiarism_priority_papers)}")
        
        return {
            "cited_draft": cited_sections,
            "citations_added": len(all_references),
            "plagiarism_citations": flagged_sentences_cited,
            "references": all_references,
            "citation_map": citation_map
        }
    
    def _format_references_section(self, references: List[Dict], citation_style: str) -> str:
        """Format references section"""
        if citation_style == "ieee":
            # IEEE: Numbered list
            references_text = "## References\n\n"
            for i, ref in enumerate(references, 1):
                references_text += f"[{i}] {ref['reference']}\n\n"
        elif citation_style == "apa":
            # APA: Alphabetical by author
            references_text = "## References\n\n"
            # Sort by author last name
            sorted_refs = sorted(references, key=lambda x: x['paper_info']['authors'].split(',')[0])
            for ref in sorted_refs:
                references_text += f"{ref['reference']}\n\n"
        else:
            # MLA or other
            references_text = "## References\n\n"
            for ref in references:
                references_text += f"{ref['reference']}\n\n"
        
        return references_text
    
    def create_citation_report(self, citation_data: Dict) -> str:
        """Create a report of citations added"""
        cited_draft = citation_data["cited_draft"]
        references = citation_data["references"]
        citation_map = citation_data.get("citation_map", {})
        
        report = "=" * 80 + "\n"
        report += "                    CITATION ANALYSIS REPORT\n"
        report += "=" * 80 + "\n\n"
        
        report += "📊 CITATION STATISTICS\n"
        report += "-" * 40 + "\n"
        report += f"Total citations added: {citation_data['citations_added']}\n"
        report += f"Unique papers cited: {len(set(ref['paper_info']['title'] for ref in references))}\n\n"
        
        report += "📚 PAPERS CITED\n"
        report += "-" * 40 + "\n"
        
        for i, ref in enumerate(references, 1):
            paper_info = ref['paper_info']
            report += f"{i}. {paper_info['title']}\n"
            report += f"   Authors: {paper_info['authors']}\n"
            report += f"   Year: {paper_info['year']}\n"
            report += f"   Source: {paper_info['source']}\n"
            report += f"   Citation: {ref['in_text']}\n\n"
        
        report += "📄 CITATION PLACEMENT\n"
        report += "-" * 40 + "\n"
        
        for section_name, section_text in cited_draft.items():
            if section_name != "references":
                # Count citations in this section
                citation_count = sum(1 for ref in references 
                                   if ref['paper_info']['title'] in citation_map and 
                                   section_name in citation_map[ref['paper_info']['title']].get('cited_in', []))
                
                if citation_count > 0:
                    report += f"• {section_name}: {citation_count} citations\n"
        
        report += "\n" + "=" * 80 + "\n"
        
        return report


# Test function
if __name__ == "__main__":
    print("🧪 Testing Citation Agent")
    print("=" * 60)
    
    agent = CitationAgent()
    
    # Test with sample data
    test_draft = {
        "abstract": "Deep learning has shown promising results in stock market prediction. Various approaches have been proposed in recent literature.",
        "introduction": "Stock market prediction is a challenging task due to market volatility. Previous research has demonstrated the effectiveness of LSTM networks for time series forecasting. However, traditional methods often fail to capture complex patterns.",
        "related_work": "Early work on stock prediction used statistical methods. More recent studies have focused on deep learning approaches. A survey by Smith et al. provides comprehensive coverage of existing methods."
    }
    
    test_papers = [
        {
            "title": "LSTM Neural Networks for Stock Market Prediction",
            "authors_str": "John Smith, Jane Doe",
            "published": "2021-06-15",
            "primary_category": "cs.LG",
            "abstract": "This paper presents LSTM networks for stock prediction with improved accuracy.",
            "relevance": 0.9,
            "doi": "10.1000/example"
        },
        {
            "title": "A Survey of Deep Learning in Finance",
            "authors_str": "Alice Johnson",
            "published": "2022-03-10",
            "primary_category": "cs.AI",
            "abstract": "Comprehensive survey of deep learning applications in financial markets.",
            "relevance": 0.85,
            "doi": "10.2000/survey"
        }
    ]
    
    result = agent.add_citations_to_draft(test_draft, test_papers, citation_style="apa")
    
    print("\n📝 Original Abstract:")
    print(test_draft["abstract"])
    
    print("\n📝 Cited Abstract:")
    print(result["cited_draft"]["abstract"])
    
    print("\n📚 References:")
    print(result["cited_draft"]["references"])
    
    print("\n📊 Report:")
    report = agent.create_citation_report(result)
    print(report)