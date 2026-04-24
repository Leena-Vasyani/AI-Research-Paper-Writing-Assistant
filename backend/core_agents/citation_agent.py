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
        Identify sentences/claims that need citations.
        Now uses a simpler, more effective approach that catches most academic claims.
        """
        citation_needs = []
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', draft_text.strip())
        current_pos = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Must be meaningful length
            if len(sentence.split()) < 3:
                current_pos += len(sentence) + 1
                continue
            
            sentence_lower = sentence.lower()
            needs_citation = False
            
            # Check for academic indicators that need citations
            academic_keywords = [
                # Claims about findings
                r'show|shows|shown|demonstrated|demonstrates|demonstrated|proven|proves|found|findings?|result',
                # Referential language
                r'previous|prior|existing|earlier|recent|current|latest|literature|research|study|studies|work',
                # Citation indicators
                r'according to|as per|based on|following|reported|described|noted|proposed|suggested|argued',
                # Comparative language
                r'similar|comparable|comparable|different|unlike|contrast|comparison|compared to|versus',
                # Methods/approaches
                r'method|approach|technique|algorithm|model|framework|strategy',
                # General knowledge claims
                r'typically|commonly|usually|often|generally|traditionally|standard|conventional'
            ]
            
            for keyword_pattern in academic_keywords:
                if re.search(keyword_pattern, sentence_lower):
                    needs_citation = True
                    break
            
            if needs_citation:
                citation_needs.append((sentence, current_pos))
            
            current_pos += len(sentence) + 1
        
        return citation_needs
    
    def find_relevant_citations(self, citation_sentence: str, retrieved_papers: List[Dict]) -> List[Dict]:
        """
        Find relevant papers to cite for a given sentence.
        Now uses more lenient matching to ensure papers are found.
        """
        if not retrieved_papers:
            return []
        
        relevant_papers = []
        sentence_terms = self._extract_key_terms(citation_sentence)
        
        # If no terms extracted, use the sentence as-is
        if not sentence_terms:
            sentence_terms = citation_sentence.lower().split()[:5]
        
        for paper in retrieved_papers:
            relevance_score = self._calculate_citation_relevance(
                citation_sentence, 
                sentence_terms,
                paper
            )
            
            # Lower threshold to catch more relevant papers
            if relevance_score > 0.1:
                relevant_papers.append({
                    "paper": paper,
                    "relevance_score": relevance_score,
                    "citation_type": self._determine_citation_type(citation_sentence, paper)
                })
        
        # Sort by relevance
        relevant_papers.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_papers[:3]
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text for matching - less aggressive filtering"""
        text = text.lower().translate(str.maketrans('', '', string.punctuation))
        
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 
            'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
            'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'as', 'from'
        }
        
        words = text.split()
        # Keep words that are 2+ chars and not stop words (was >3, too aggressive)
        key_terms = [word for word in words if word not in stop_words and len(word) >= 2]
        
        return key_terms[:8]  # Limit to top 8 terms for efficiency
    
    def _calculate_citation_relevance(self, sentence: str, sentence_terms: List[str], paper: Dict) -> float:
        """Calculate relevance between sentence and paper - more generous scoring"""
        score = 0.0
        
        if not sentence_terms:
            return 0.0
        
        # Check paper title - weight increased
        title = paper.get('title', '').lower()
        if title:
            title_matches = sum(1 for term in sentence_terms if term in title)
            title_score = min(title_matches / len(sentence_terms), 1.0)
            score += title_score * 0.5
        
        # Check abstract
        abstract = paper.get('abstract', '').lower()
        if abstract:
            abstract_matches = sum(1 for term in sentence_terms if term in abstract)
            abstract_score = min(abstract_matches / len(sentence_terms), 1.0)
            score += abstract_score * 0.3
        
        # Check relevance score from retrieval (if available)
        relevance = paper.get('relevance_score', paper.get('relevance', 0.0))
        score += relevance * 0.2
        
        # Add recency bonus
        published = paper.get('published', '')
        if published:
            try:
                year = int(published[:4])
                current_year = datetime.now().year
                age = current_year - year
                
                # More lenient: papers from last 15 years get decent score
                if age <= 5:
                    recency_score = 1.0
                elif age <= 10:
                    recency_score = 0.8
                elif age <= 15:
                    recency_score = 0.6
                else:
                    recency_score = max(0.2, 1.0 - (age - 15) / 20)
                
                score += recency_score * 0.05
            except:
                pass
        
        return min(score, 1.0)
    
    def _determine_citation_type(self, sentence: str, paper: Dict) -> str:
        """Determine what type of citation this should be"""
        sentence_lower = sentence.lower()
        paper_title = paper.get('title', '').lower()
        
        if any(word in sentence_lower for word in ['method', 'approach', 'technique', 'algorithm']):
            return "method"
        elif any(word in sentence_lower for word in ['result', 'finding', 'shows', 'demonstrates']):
            return "result"
        elif any(word in sentence_lower for word in ['review', 'survey', 'overview']):
            return "review"
        
        return "general"
    
    def format_citation(self, paper: Dict, citation_style: str = "apa", citation_number: int = None) -> Dict:
        """Format citation in specified style"""
        style = self.citation_styles.get(citation_style, self.citation_styles["apa"])
        
        # Extract author information
        authors_str = paper.get('authors_str', 'Unknown Author')
        authors = authors_str.split(',') if authors_str else ['Unknown Author']
        
        first_author = authors[0].strip() if authors else 'Unknown Author'
        
        # Parse author name
        if ' ' in first_author:
            author_parts = first_author.split()
            author_last = author_parts[-1]
            author_first_initial = author_parts[0][0].upper() + '.'
        else:
            author_last = first_author
            author_first_initial = first_author[0].upper() + '.' if first_author else 'A.'
        
        # Extract year
        published = paper.get('published', '')
        try:
            year = published[:4] if published else 'n.d.'
        except:
            year = 'n.d.'
        
        # Extract title
        title = paper.get('title', 'Unknown Title')
        
        # Format journal/source
        journal = paper.get('primary_category', 'arXiv').replace('.', ' ')
        
        # Get DOI/URL
        doi = paper.get('doi', '') or paper.get('pdf_url', '')
        
        # Create formatted citations
        in_text_citation = style["in_text"].format(
            author=author_last,
            year=year,
            number=citation_number if citation_number else 1,
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
            number=citation_number if citation_number else 1,
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
    
    def _build_full_draft(self, cited_sections: Dict[str, str]) -> str:
        """
        Build a complete formatted draft with all sections and references.
        """
        output = ""
        
        # Display each section except references
        for section_name, section_text in cited_sections.items():
            if section_name.lower() == "references":
                continue
            
            output += f"## {section_name.upper()}\n\n"
            output += section_text + "\n\n"
        
        # Add references at the end
        if "references" in cited_sections:
            output += cited_sections["references"]
        
        return output
    
    def add_citations_to_draft(self, draft_sections: Dict[str, str], 
                              retrieved_papers: List[Dict],
                              plagiarism_results: Dict = None,
                              citation_style: str = "ieee") -> Dict:
        """
        Add citations to draft sections intelligently.
        MAIN METHOD - fully functional without plagiarism results.
        Uses IEEE style by default for [1], [2] format.
        """
        if plagiarism_results:
            return self.add_citations_to_draft_with_plagiarism(
                draft_sections, retrieved_papers, plagiarism_results, citation_style
            )
        
        print("\n📝 Adding Intelligent Citations...")
        print("-" * 70)
        
        cited_sections = {}
        all_references = []
        citation_map = {}  # Maps paper IDs to citation numbers
        
        for section_name, section_text in draft_sections.items():
            if section_name.lower() == "references" or not section_text:
                cited_sections[section_name] = section_text
                continue
            
            print(f"\n  📄 Processing {section_name}...")
            
            # Extract sentences that need citations
            citation_needs = self.extract_citation_needs(section_text)
            print(f"     Found {len(citation_needs)} potential citation points")
            
            cited_text = section_text
            added_citations = 0
            
            # Process each sentence that needs citation
            for sentence, position in citation_needs:
                # Find relevant papers
                relevant_papers = self.find_relevant_citations(sentence, retrieved_papers)
                
                if relevant_papers:
                    # Use the most relevant paper
                    paper = relevant_papers[0]["paper"]
                    paper_id = paper.get('id') or paper.get('title', f'paper_{len(all_references)}')
                    
                    # Check if this paper was already cited
                    if paper_id not in citation_map:
                        citation_number = len(all_references) + 1
                        formatted_citation = self.format_citation(paper, citation_style, citation_number)
                        
                        citation_map[paper_id] = {
                            "number": citation_number,
                            "formatted": formatted_citation,
                            "sections": [section_name]
                        }
                        all_references.append(formatted_citation)
                    else:
                        citation_number = citation_map[paper_id]["number"]
                        formatted_citation = citation_map[paper_id]["formatted"]
                        if section_name not in citation_map[paper_id]["sections"]:
                            citation_map[paper_id]["sections"].append(section_name)
                    
                    # Insert citation [#] at the end of the sentence
                    in_text_citation = f"[{citation_number}]"
                    
                    # Find the sentence in the current text and add citation
                    if sentence in cited_text:
                        # Find position of sentence in current text
                        sent_pos = cited_text.find(sentence)
                        if sent_pos != -1:
                            sent_end = sent_pos + len(sentence)
                            # Insert citation before period/punctuation
                            if sent_end < len(cited_text) and cited_text[sent_end] in '.!?':
                                cited_text = cited_text[:sent_end] + f" {in_text_citation}" + cited_text[sent_end:]
                            else:
                                cited_text = cited_text[:sent_end] + f" {in_text_citation}" + cited_text[sent_end:]
                            
                            added_citations += 1
            
            cited_sections[section_name] = cited_text
            print(f"     ✅ Added {added_citations} citations")
        
        # Add references section
        references_text = self._format_references_section(all_references, citation_style)
        cited_sections["references"] = references_text
        
        print(f"\n{'='*70}")
        print(f"✅ CITATION RESULTS")
        print(f"{'='*70}")
        print(f"Total citations added: {len(all_references)}")
        print(f"Unique papers cited: {len(set(ref['paper_info']['title'] for ref in all_references))}")
        print(f"{'='*70}\n")
        
        # Build the full draft with all sections
        full_draft = self._build_full_draft(cited_sections)
        
        return {
            "cited_draft": cited_sections,
            "citations_added": len(all_references),
            "references": all_references,
            "citation_map": citation_map,
            "full_draft": full_draft
        }
    
    def add_citations_to_draft_with_plagiarism(self, draft_sections: Dict[str, str], 
                                              retrieved_papers: List[Dict],
                                              plagiarism_results: Dict = None,
                                              citation_style: str = "ieee") -> Dict:
        """
        Add citations intelligently, prioritizing flagged plagiarized sentences.
        Uses IEEE style [1], [2] format by default.
        """
        print("\n📝 Adding Intelligent Citations (with Plagiarism Priority)...")
        print("-" * 70)
        
        cited_sections = {}
        all_references = []
        citation_map = {}
        flagged_sentences_cited = 0
        
        for section_name, section_text in draft_sections.items():
            if section_name.lower() == "references" or not section_text:
                cited_sections[section_name] = section_text
                continue
            
            print(f"\n  🎯 Processing {section_name}...")
            
            # Extract plagiarism flags for this section
            section_plagiarism = {}
            if plagiarism_results and ('section_analysis' in plagiarism_results or 'section_analyses' in plagiarism_results):
                analyses = plagiarism_results.get('section_analysis', plagiarism_results.get('section_analyses', {}))
                section_data = analyses.get(section_name, {})
                flagged = section_data.get('flagged_sentences', [])
                
                # Create mapping of sentences to their source papers
                for flag in flagged:
                    sentence = flag.get('sentence', '')
                    source = flag.get('source', flag.get('source_match', ''))
                    similarity = flag.get('similarity', flag.get('similarity_score', 0))
                    section_plagiarism[sentence] = {
                        'source': source,
                        'similarity': similarity
                    }
            
            cited_text = section_text
            citation_count = 0
            
            # PRIORITY 1: Cite flagged (plagiarized) sentences
            for flagged_sentence, plag_info in section_plagiarism.items():
                # Find this sentence in the text
                if flagged_sentence in cited_text:
                    sentence_to_cite = flagged_sentence
                else:
                    # Try fuzzy matching
                    sentences = re.split(r'[.!?]+', section_text)
                    best_match = None
                    best_score = 0
                    
                    for s in sentences:
                        s = s.strip()
                        if len(s) > 10:
                            flagged_words = set(flagged_sentence.lower().split())
                            text_words = set(s.lower().split())
                            if flagged_words and text_words:
                                overlap = len(flagged_words & text_words) / len(flagged_words)
                                if overlap > best_score and overlap > 0.5:
                                    best_score = overlap
                                    best_match = s
                    
                    sentence_to_cite = best_match if best_match else None
                
                if not sentence_to_cite:
                    continue
                
                # Find best paper to cite
                source_title = plag_info.get('source', '')
                relevant = self.find_relevant_citations(sentence_to_cite, retrieved_papers)
                
                if relevant:
                    paper = relevant[0]["paper"]
                    paper_id = paper.get('id') or paper.get('title', f'paper_{len(all_references)}')
                    
                    if paper_id not in citation_map:
                        citation_number = len(all_references) + 1
                        formatted = self.format_citation(paper, citation_style, citation_number)
                        
                        citation_map[paper_id] = {
                            "number": citation_number,
                            "formatted": formatted,
                            "sections": [section_name],
                            "plagiarism_flagged": True
                        }
                        all_references.append(formatted)
                    else:
                        citation_number = citation_map[paper_id]["number"]
                        formatted = citation_map[paper_id]["formatted"]
                        if section_name not in citation_map[paper_id]["sections"]:
                            citation_map[paper_id]["sections"].append(section_name)
                    
                    # Insert citation [#]
                    in_text_citation = f"[{citation_number}]"
                    if sentence_to_cite in cited_text:
                        pos = cited_text.find(sentence_to_cite)
                        end_pos = pos + len(sentence_to_cite)
                        if end_pos < len(cited_text) and cited_text[end_pos] in '.!?':
                            cited_text = cited_text[:end_pos] + f" {in_text_citation}" + cited_text[end_pos:]
                        else:
                            cited_text = cited_text[:end_pos] + f" {in_text_citation}" + cited_text[end_pos:]
                        
                        citation_count += 1
                        flagged_sentences_cited += 1
            
            # PRIORITY 2: Cite other academic claims
            additional = self.extract_citation_needs(section_text)
            for sentence, _ in additional[:3]:
                # Skip already flagged
                if any(fs in sentence for fs in section_plagiarism.keys()):
                    continue
                
                relevant = self.find_relevant_citations(sentence, retrieved_papers)
                if relevant:
                    paper = relevant[0]["paper"]
                    paper_id = paper.get('id') or paper.get('title', f'paper_{len(all_references)}')
                    
                    if paper_id not in citation_map:
                        citation_number = len(all_references) + 1
                        formatted = self.format_citation(paper, citation_style, citation_number)
                        
                        citation_map[paper_id] = {
                            "number": citation_number,
                            "formatted": formatted,
                            "sections": [section_name],
                            "plagiarism_flagged": False
                        }
                        all_references.append(formatted)
                    else:
                        citation_number = citation_map[paper_id]["number"]
                        formatted = citation_map[paper_id]["formatted"]
                    
                    in_text_citation = f"[{citation_number}]"
                    if sentence in cited_text:
                        pos = cited_text.find(sentence)
                        end_pos = pos + len(sentence)
                        if end_pos < len(cited_text) and cited_text[end_pos] in '.!?':
                            cited_text = cited_text[:end_pos] + f" {in_text_citation}" + cited_text[end_pos:]
                        else:
                            cited_text = cited_text[:end_pos] + f" {in_text_citation}" + cited_text[end_pos:]
                        
                        citation_count += 1
            
            cited_sections[section_name] = cited_text
            print(f"     ✅ Added {citation_count} citations")
        
        # Format references
        references_text = self._format_references_section(all_references, citation_style)
        cited_sections["references"] = references_text
        
        print(f"\n{'='*70}")
        print(f"✅ CITATION RESULTS")
        print(f"{'='*70}")
        print(f"Plagiarism-flagged citations: {flagged_sentences_cited}")
        print(f"Total citations added: {len(all_references)}")
        print(f"Unique papers: {len(set(ref['paper_info']['title'] for ref in all_references))}")
        print(f"{'='*70}\n")
        
        # Build the full draft with all sections
        full_draft = self._build_full_draft(cited_sections)
        
        return {
            "cited_draft": cited_sections,
            "citations_added": len(all_references),
            "plagiarism_citations": flagged_sentences_cited,
            "references": all_references,
            "citation_map": citation_map,
            "full_draft": full_draft
        }
    
    def _format_references_section(self, references: List[Dict], citation_style: str) -> str:
        """Format references section"""
        if not references:
            return "## References\n\nNo references.\n"
        
        references_text = "## References\n\n"
        
        # Use IEEE numbering by default
        for i, ref in enumerate(references, 1):
            references_text += f"[{i}] {ref['reference']}\n\n"
        
        return references_text
    
    def display_cited_draft(self, citation_result: Dict) -> str:
        """
        Display the complete cited draft with all sections and references.
        """
        output = "\n" + "="*80 + "\n"
        output += "📄 CITED DRAFT\n"
        output += "="*80 + "\n\n"
        
        cited_draft = citation_result["cited_draft"]
        
        # Display each section
        for section_name, section_text in cited_draft.items():
            if section_name.lower() == "references":
                continue  # Handle references separately
            
            output += f"## {section_name.upper()}\n"
            output += "-" * 80 + "\n"
            output += section_text + "\n\n"
        
        # Display references at the end
        if "references" in cited_draft:
            output += cited_draft["references"]
        
        output += "\n" + "="*80 + "\n"
        return output
    
    def create_citation_report(self, citation_data: Dict) -> str:
        """Create a report of citations added"""
        report = "\n" + "=" * 80 + "\n"
        report += "CITATION ANALYSIS REPORT\n"
        report += "=" * 80 + "\n\n"
        
        report += f"Total citations added: {citation_data['citations_added']}\n"
        report += f"Total papers cited: {len(set(ref['paper_info']['title'] for ref in citation_data['references']))}\n\n"
        
        report += "Papers Cited:\n"
        report += "-" * 40 + "\n"
        for i, ref in enumerate(citation_data['references'], 1):
            info = ref['paper_info']
            report += f"[{i}] {info['title']}\n"
            report += f"    Authors: {info['authors']}\n"
            report += f"    Year: {info['year']}\n"
            report += f"    Source: {info['source']}\n\n"
        
        report += "=" * 80 + "\n"
        return report


# Test function
if __name__ == "__main__":
    print("🧪 Testing Citation Agent")
    print("=" * 80)
    
    agent = CitationAgent()
    
    test_draft = {
        "abstract": "Deep learning has shown promising results in stock market prediction. Various approaches have been proposed in recent literature.",
        "introduction": "Stock market prediction is a challenging task due to market volatility. Previous research has demonstrated the effectiveness of LSTM networks for time series forecasting. However, traditional methods often fail to capture complex patterns.",
        "methods": "The study used deep neural networks for prediction."
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
    
    result = agent.add_citations_to_draft(test_draft, test_papers, citation_style="ieee")
    
    # Display the cited draft
    print(agent.display_cited_draft(result))
    
    # Display the report
    print(agent.create_citation_report(result))