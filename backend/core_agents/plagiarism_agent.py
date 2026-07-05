"""
Plagiarism Detection Agent
==========================
Detects plagiarism in generated research paper drafts by comparing against source papers.

Features:
- Sentence-level similarity detection
- Multi-level scoring (Good < 30%, Moderate 30-50%, High > 50%)
- Section-wise analysis
- Detailed plagiarism reports
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime
import random
import requests
import time


class PlagiarismDetectionAgent:
    """
    Professional plagiarism detection agent for research papers.
    Compares generated drafts against source papers using semantic similarity.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize plagiarism detection agent
        
        Args:
            model_name: Sentence transformer model for similarity detection
        """
        print(f"🔄 Loading plagiarism detection model: {model_name}")
        try:
            self.model = SentenceTransformer(model_name, device="cpu")
            print("✅ Plagiarism detection model loaded successfully")
        except Exception as e:
            print(f"⚠️ Error loading model: {e}")
            raise
        
        # Plagiarism thresholds
        self.thresholds = {
            'low': 0.30,      # < 30% = Good
            'moderate': 0.50,  # 30-50% = Moderate
            'high': 0.50       # > 50% = High plagiarism
        }
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences for granular analysis
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple sentence splitting using regex
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter
        cleaned_sentences = []
        for sent in sentences:
            sent = sent.strip()
            # Keep sentences with at least 5 words
            if sent and len(sent.split()) >= 5:
                cleaned_sentences.append(sent)
        
        return cleaned_sentences
    
    def _extract_source_content(self, papers: List[Dict]) -> Dict[str, List[str]]:
        """
        Extract text content from source papers
        
        Args:
            papers: List of retrieved papers
            
        Returns:
            Dictionary with paper titles and their sentences
        """
        source_content = {}
        
        for i, paper in enumerate(papers):
            title = paper.get('title', f'Paper {i+1}')
            
            # Combine abstract and available text
            text_parts = []
            
            if 'abstract' in paper and paper['abstract']:
                text_parts.append(paper['abstract'])
            
            # If full text is available (from summarization phase)
            if 'full_text' in paper and paper['full_text']:
                text_parts.append(paper['full_text'][:5000])  # Limit to first 5000 chars
            
            combined_text = ' '.join(text_parts)
            
            if combined_text:
                sentences = self._split_into_sentences(combined_text)
                source_content[title] = sentences
        
        return source_content
    
    def _calculate_sentence_similarity(self, draft_sentence: str, 
                                      source_sentences: List[str]) -> Tuple[float, str]:
        """
        Calculate maximum similarity between a draft sentence and source sentences
        
        Args:
            draft_sentence: Sentence from generated draft
            source_sentences: All sentences from source papers
            
        Returns:
            Tuple of (max_similarity_score, most_similar_sentence)
        """
        if not source_sentences:
            return 0.0, ""
        
        try:
            # Encode draft sentence
            draft_embedding = self.model.encode([draft_sentence])
            
            # Encode source sentences (in batches for efficiency)
            batch_size = 100
            max_similarity = 0.0
            most_similar = ""
            
            for i in range(0, len(source_sentences), batch_size):
                batch = source_sentences[i:i+batch_size]
                source_embeddings = self.model.encode(batch)
                
                # Calculate similarities
                similarities = cosine_similarity(draft_embedding, source_embeddings)[0]
                
                # Track maximum
                batch_max_idx = np.argmax(similarities)
                batch_max_sim = similarities[batch_max_idx]
                
                if batch_max_sim > max_similarity:
                    max_similarity = batch_max_sim
                    most_similar = batch[batch_max_idx]
            
            return float(max_similarity), most_similar
            
        except Exception as e:
            print(f"⚠️ Error calculating similarity: {e}")
            return 0.0, ""
    
    def _analyze_section(self, section_text: str, source_content: Dict[str, List[str]],
                        section_name: str) -> Dict:
        """
        Analyze plagiarism in a single section
        
        Args:
            section_text: Text of the section to analyze
            source_content: Dictionary of source paper content
            section_name: Name of the section
            
        Returns:
            Dictionary with section analysis results
        """
        print(f"   📊 Analyzing section: {section_name}")
        
        # Split section into sentences
        draft_sentences = self._split_into_sentences(section_text)
        
        if not draft_sentences:
            return {
                'section_name': section_name,
                'total_sentences': 0,
                'plagiarism_score': 0.0,
                'flagged_sentences': [],
                'status': 'empty'
            }
        
        # Combine all source sentences
        all_source_sentences = []
        for paper_sentences in source_content.values():
            all_source_sentences.extend(paper_sentences)
        
        if not all_source_sentences:
            return {
                'section_name': section_name,
                'total_sentences': len(draft_sentences),
                'plagiarism_score': 0.0,
                'flagged_sentences': [],
                'status': 'no_sources'
            }
        
        # Analyze each sentence
        flagged_sentences = []
        total_similarity = 0.0
        
        for idx, sentence in enumerate(draft_sentences):
            similarity, source_match = self._calculate_sentence_similarity(
                sentence, all_source_sentences
            )
            
            total_similarity += similarity
            
            # Flag sentences above low threshold
            if similarity >= self.thresholds['low']:
                severity = 'high' if similarity >= self.thresholds['high'] else 'moderate'
                
                flagged_sentences.append({
                    'sentence_index': idx,
                    'sentence': sentence,
                    'similarity_score': float(similarity),
                    'severity': severity,
                    'source_match': source_match,
                    'needs_rewrite': True
                })
        
        # Calculate overall section score
        avg_similarity = total_similarity / len(draft_sentences)
        
        # Determine status
        if avg_similarity < self.thresholds['low']:
            status = 'good'
        elif avg_similarity < self.thresholds['high']:
            status = 'moderate'
        else:
            status = 'high_plagiarism'
        
        return {
            'section_name': section_name,
            'total_sentences': len(draft_sentences),
            'plagiarism_score': float(avg_similarity * 100),  # Convert to percentage
            'flagged_sentences': flagged_sentences,
            'status': status,
            'sentences_flagged': len(flagged_sentences)
        }
    
    def check_plagiarism(self, generated_draft: Dict[str, str], 
                        source_papers: List[Dict],
                        research_topic: str) -> Dict:
        """
        Complete plagiarism check of generated draft against source papers
        
        Args:
            generated_draft: Dictionary with sections (abstract, introduction, related_work)
            source_papers: List of retrieved source papers
            research_topic: Research topic for context
            
        Returns:
            Comprehensive plagiarism report
        """
        print(f"\n{'='*80}")
        print(f"🔍 PLAGIARISM DETECTION ANALYSIS")
        print(f"Topic: {research_topic}")
        print(f"Source Papers: {len(source_papers)}")
        print(f"{'='*80}\n")
        
        # Extract source content
        print("📥 Extracting source content...")
        source_content = self._extract_source_content(source_papers)
        print(f"   ✅ Extracted content from {len(source_content)} papers")
        
        # Count total source sentences
        total_source_sentences = sum(len(sents) for sents in source_content.values())
        print(f"   📊 Total source sentences: {total_source_sentences}")
        
        if total_source_sentences == 0:
            print("   ⚠️ No source content available for comparison")
            return self._create_no_source_report(generated_draft, research_topic)
        
        # Analyze each section
        print(f"\n🔬 Analyzing sections:")
        print("-" * 40)
        
        section_analyses = []

        # Analyze EVERY non-empty section in the draft, keyed by its actual
        # (display) name. The draft dict uses display names like "Abstract",
        # "Introduction", "Methodology" — not the old hardcoded lowercase keys —
        # so iterate the dict directly and skip References / empty sections.
        total_sentences = 0
        total_flagged = 0
        weighted_score = 0.0

        for section_name, section_text in (generated_draft or {}).items():
            if not section_text or not str(section_text).strip():
                continue
            if str(section_name).strip().lower() == 'references':
                continue

            analysis = self._analyze_section(str(section_text), source_content, str(section_name))
            section_analyses.append(analysis)

            total_sentences += analysis['total_sentences']
            total_flagged += analysis['sentences_flagged']
            weighted_score += analysis['plagiarism_score'] * analysis['total_sentences']

            # Print progress
            status_icon = "✅" if analysis['status'] == 'good' else "⚠️" if analysis['status'] == 'moderate' else "🚨"
            print(f"   {status_icon} {section_name}: {analysis['plagiarism_score']:.1f}% "
                  f"({analysis['sentences_flagged']}/{analysis['total_sentences']} flagged)")
        
        # Calculate overall plagiarism score
        overall_score = weighted_score / total_sentences if total_sentences > 0 else 0.0
        
        # Determine overall status
        if overall_score < self.thresholds['low'] * 100:
            overall_status = 'good'
            overall_message = "Low plagiarism detected. Draft appears original."
        elif overall_score < self.thresholds['high'] * 100:
            overall_status = 'moderate'
            overall_message = "Moderate plagiarism detected. Review flagged sections."
        else:
            overall_status = 'high_plagiarism'
            overall_message = "High plagiarism detected! Significant rewriting required."
        
        # Compile report
        report = {
            'metadata': {
                'research_topic': research_topic,
                'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'source_papers_count': len(source_papers),
                'total_source_sentences': total_source_sentences
            },
            'overall_score': float(overall_score),
            'overall_status': overall_status,
            'overall_message': overall_message,
            'statistics': {
                'total_sentences': total_sentences,
                'sentences_flagged': total_flagged,
                'percentage_flagged': (total_flagged / total_sentences * 100) if total_sentences > 0 else 0.0
            },
            'section_analyses': section_analyses,
            'thresholds': {
                'good': self.thresholds['low'] * 100,
                'moderate': self.thresholds['high'] * 100
            }
        }
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"📊 PLAGIARISM ANALYSIS COMPLETE")
        print(f"Overall Score: {overall_score:.1f}%")
        print(f"Status: {overall_status.upper()}")
        print(f"Flagged: {total_flagged}/{total_sentences} sentences ({report['statistics']['percentage_flagged']:.1f}%)")
        print(f"{'='*80}\n")
        
        return report
    
    def _create_no_source_report(self, generated_draft: Dict[str, str], 
                                 research_topic: str) -> Dict:
        """
        Create a report when no source content is available
        """
        return {
            'metadata': {
                'research_topic': research_topic,
                'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'source_papers_count': 0,
                'total_source_sentences': 0
            },
            'overall_score': 0.0,
            'overall_status': 'no_sources',
            'overall_message': "No source content available for plagiarism check.",
            'statistics': {
                'total_sentences': 0,
                'sentences_flagged': 0,
                'percentage_flagged': 0.0
            },
            'section_analyses': [],
            'thresholds': {
                'good': self.thresholds['low'] * 100,
                'moderate': self.thresholds['high'] * 100
            }
        }
    
    def _generate_paraphrasing_suggestions(self, sentence: str, 
                                          similarity_score: float) -> List[str]:
        """
        Generate detailed paraphrasing suggestions for a plagiarized sentence
        
        Args:
            sentence: Flagged sentence
            similarity_score: Similarity score to source
            
        Returns:
            List of specific suggestions for rewriting
        """
        suggestions = []
        
        # Analyze the sentence structure
        words = sentence.split()
        word_count = len(words)
        
        # Different strategies based on similarity level
        if similarity_score >= 0.70:  # High similarity
            suggestions.append("🚨 HIGH SIMILARITY: Complete rewrite recommended")
            suggestions.append("   → Restructure the entire sentence with new phrasing")
            suggestions.append("   → Change sentence structure (active ↔ passive voice)")
            suggestions.append("   → Use different synonyms for key terms")
            suggestions.append("   → Break into multiple sentences or combine with adjacent ideas")
            
        elif similarity_score >= 0.50:  # Moderate similarity
            suggestions.append("⚠️ MODERATE SIMILARITY: Significant paraphrasing needed")
            suggestions.append("   → Reorder clauses and phrases")
            suggestions.append("   → Replace key phrases with synonyms or alternatives")
            suggestions.append("   → Change technical terms to equivalent expressions")
            
        else:  # Low-moderate similarity
            suggestions.append("ℹ️ MILD SIMILARITY: Minor paraphrasing suggested")
            suggestions.append("   → Replace some keywords with synonyms")
            suggestions.append("   → Adjust sentence opening and structure")
        
        # Add specific paraphrasing techniques
        suggestions.append("\n💡 PARAPHRASING TECHNIQUES:")
        
        # Technique 1: Synonym replacement
        suggestions.append("   1. Synonym Replacement:")
        suggestions.append("      - Replace common words with academic alternatives")
        suggestions.append("      - Example: 'shows' → 'demonstrates', 'uses' → 'employs'")
        
        # Technique 2: Sentence restructuring
        suggestions.append("   2. Sentence Restructuring:")
        if "is" in sentence or "are" in sentence or "was" in sentence:
            suggestions.append("      - Convert passive voice to active (or vice versa)")
        suggestions.append("      - Start with a different clause")
        suggestions.append("      - Change from simple to complex sentence structure")
        
        # Technique 3: Concept reframing
        suggestions.append("   3. Concept Reframing:")
        suggestions.append("      - Express the same idea using different concepts")
        suggestions.append("      - Add qualifiers or context to differentiate")
        suggestions.append("      - Cite your interpretation of the source idea")
        
        # Technique 4: Word choice improvement
        if word_count > 15:
            suggestions.append("   4. Simplification:")
            suggestions.append("      - Sentence is lengthy - consider splitting")
            suggestions.append("      - Break into 2-3 shorter, clearer sentences")
        
        return suggestions
    
    def _generate_rewrite_examples(self, sentence: str, 
                                   source_match: str) -> List[Dict[str, str]]:
        """
        Generate example rewrites of a plagiarized sentence
        
        Args:
            sentence: Original flagged sentence
            source_match: Source sentence it matches
            
        Returns:
            List of rewrite examples with explanations
        """
        examples = []
        
        # Example 1: Synonym substitution
        examples.append({
            'strategy': 'Synonym Substitution',
            'description': 'Replace key words with synonyms while maintaining meaning',
            'note': 'Maintain technical accuracy when changing terms'
        })
        
        # Example 2: Restructuring
        examples.append({
            'strategy': 'Sentence Restructuring',
            'description': 'Change sentence order and structure (active/passive voice)',
            'note': 'Improves originality while preserving core information'
        })
        
        # Example 3: Concept reframing
        examples.append({
            'strategy': 'Concept Reframing',
            'description': 'Express the same idea from a different perspective',
            'note': 'Add your analysis or interpretation of the concept'
        })
        
        # Example 4: Add citations
        examples.append({
            'strategy': 'Proper Attribution',
            'description': 'Use quotation marks and citations for direct ideas from sources',
            'note': 'Format: "According to [Author], ..." or paraphrase with [Citation]'
        })
        
        return examples
    
    def generate_detailed_suggestions(self, report: Dict) -> Dict:
        """
        Enhance plagiarism report with detailed rewrite suggestions
        
        Args:
            report: Base plagiarism report
            
        Returns:
            Enhanced report with detailed suggestions for each flagged sentence
        """
        print(f"\n{'='*80}")
        print(f"💡 GENERATING DETAILED REWRITE SUGGESTIONS")
        print(f"{'='*80}\n")
        
        suggestions_added = 0
        
        for section in report['section_analyses']:
            if section['flagged_sentences']:
                print(f"   📝 Processing {section['section_name']}: "
                      f"{len(section['flagged_sentences'])} flagged sentences")
                
                for flagged in section['flagged_sentences']:
                    # Generate paraphrasing suggestions
                    suggestions = self._generate_paraphrasing_suggestions(
                        flagged['sentence'],
                        flagged['similarity_score']
                    )
                    
                    # Generate rewrite examples
                    rewrite_examples = self._generate_rewrite_examples(
                        flagged['sentence'],
                        flagged['source_match']
                    )
                    
                    # Add to flagged sentence
                    flagged['suggestions'] = suggestions
                    flagged['rewrite_examples'] = rewrite_examples
                    suggestions_added += 1
        
        # Add summary of suggestions
        report['suggestions_summary'] = {
            'total_suggestions_generated': suggestions_added,
            'sections_with_suggestions': len([s for s in report['section_analyses'] 
                                             if s['flagged_sentences']]),
            'general_guidelines': [
                "Always paraphrase in your own words - don't just replace individual words",
                "Add your own analysis and interpretation to differentiate from sources",
                "Use proper citations when referring to specific ideas from papers",
                "Combine ideas from multiple sources to create original synthesis",
                "Restructure sentences completely rather than minor word changes"
            ]
        }
        
        print(f"\n✅ Generated {suggestions_added} detailed suggestion sets")
        print(f"{'='*80}\n")
        
        return report
    
    def _check_with_plagiarism_detector_api(self, text: str) -> Optional[Dict]:
        """
        Check text using PlagiarismDetector.net free API
        (Note: Free tier has limitations - use sparingly)
        
        Args:
            text: Text to check
            
        Returns:
            API response or None if failed
        """
        try:
            # This is a placeholder for a free plagiarism API
            # Note: Most plagiarism APIs are paid. This shows the structure.
            # You would need to sign up for an API key from a service like:
            # - Copyleaks (has free tier)
            # - PlagiarismCheck.org API
            # - SmallSEOTools API
            
            # Example structure (you need to add your API key)
            api_url = "https://api.example-plagiarism-checker.com/check"
            
            # Placeholder - would need actual API key
            api_key = None  # Set this if you have an API key
            
            if not api_key:
                print("   ℹ️ External API key not configured - skipping external check")
                return None
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text[:1000],  # Limit text length for free tier
                "language": "en"
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"   ⚠️ External API returned status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ⚠️ External API check failed: {e}")
            return None
    
    def _check_with_web_search(self, sentence: str) -> Optional[float]:
        """
        Check for plagiarism using web search (free but limited)
        Uses exact phrase search to find matches online
        
        Args:
            sentence: Sentence to check
            
        Returns:
            Confidence score (0.0-1.0) or None if check failed
        """
        try:
            # This is a simple approach using search engines
            # Note: This is very basic and not as reliable as paid APIs
            
            # Clean sentence for search
            search_query = sentence.strip()[:100]  # Limit length
            
            # You could use:
            # 1. Google Custom Search API (free tier: 100 queries/day)
            # 2. Bing Search API (has free tier)
            # 3. DuckDuckGo (no API but can scrape - not recommended)
            
            # Placeholder for demonstration
            # In production, you would implement actual API calls
            
            print(f"   ℹ️ Web search check not implemented (requires API key)")
            return None
            
        except Exception as e:
            print(f"   ⚠️ Web search failed: {e}")
            return None
    
    def check_with_external_apis(self, report: Dict, 
                                 use_web_search: bool = False) -> Dict:
        """
        Enhance plagiarism report with external API checks
        
        Args:
            report: Base plagiarism report
            use_web_search: Whether to use web search (slow, limited)
            
        Returns:
            Enhanced report with external validation
        """
        print(f"\n{'='*80}")
        print(f"🌐 EXTERNAL PLAGIARISM API VALIDATION")
        print(f"{'='*80}\n")
        
        external_checks_performed = 0
        external_matches_found = 0
        
        # Check only high-severity flagged sentences
        for section in report['section_analyses']:
            if section['flagged_sentences']:
                high_severity = [f for f in section['flagged_sentences'] 
                               if f['severity'] == 'high']
                
                if high_severity:
                    print(f"   🔍 Checking {len(high_severity)} high-severity sentences "
                          f"in {section['section_name']}")
                    
                    for flagged in high_severity[:3]:  # Limit to top 3 to save API calls
                        # Try external API check
                        api_result = self._check_with_plagiarism_detector_api(
                            flagged['sentence']
                        )
                        
                        if api_result:
                            flagged['external_check'] = {
                                'source': 'api',
                                'result': api_result,
                                'verified': True
                            }
                            external_checks_performed += 1
                            external_matches_found += 1
                        
                        # Optionally try web search
                        elif use_web_search:
                            web_score = self._check_with_web_search(flagged['sentence'])
                            if web_score:
                                flagged['external_check'] = {
                                    'source': 'web_search',
                                    'confidence': web_score,
                                    'verified': web_score > 0.7
                                }
                                external_checks_performed += 1
                                if web_score > 0.7:
                                    external_matches_found += 1
                        
                        # Rate limiting
                        time.sleep(0.5)  # Be respectful to APIs
        
        # Add external validation summary
        report['external_validation'] = {
            'checks_performed': external_checks_performed,
            'matches_found': external_matches_found,
            'api_configured': False,  # Set to True when you add API key
            'note': 'External API validation requires API keys. Configure in plagiarism_agent.py'
        }
        
        if external_checks_performed > 0:
            print(f"\n✅ External validation: {external_checks_performed} checks, "
                  f"{external_matches_found} additional matches found")
        else:
            print(f"\nℹ️ External API not configured. Using local comparison only.")
            print(f"   To enable: Add API keys in _check_with_plagiarism_detector_api()")
        
        print(f"{'='*80}\n")
        
        return report
    
    def format_report_for_export(self, report: Dict) -> str:
        """
        Format plagiarism report for text export
        
        Args:
            report: Plagiarism analysis report
            
        Returns:
            Formatted text report
        """
        lines = []
        
        # Header
        lines.append("╔══════════════════════════════════════════════════════════════════════════════╗")
        lines.append("║                     PLAGIARISM DETECTION REPORT                              ║")
        lines.append("╚══════════════════════════════════════════════════════════════════════════════╝")
        lines.append("")
        
        # Metadata
        meta = report['metadata']
        lines.append("📋 ANALYSIS METADATA")
        lines.append("─" * 80)
        lines.append(f"Research Topic: {meta['research_topic']}")
        lines.append(f"Analysis Date: {meta['analysis_date']}")
        lines.append(f"Source Papers: {meta['source_papers_count']}")
        lines.append(f"Source Sentences: {meta['total_source_sentences']}")
        lines.append("")
        
        # Overall Results
        lines.append("🎯 OVERALL RESULTS")
        lines.append("─" * 80)
        lines.append(f"Plagiarism Score: {report['overall_score']:.1f}%")
        lines.append(f"Status: {report['overall_status'].upper()}")
        lines.append(f"Message: {report['overall_message']}")
        lines.append("")
        
        # Statistics
        stats = report['statistics']
        lines.append("📊 STATISTICS")
        lines.append("─" * 80)
        lines.append(f"Total Sentences Analyzed: {stats['total_sentences']}")
        lines.append(f"Sentences Flagged: {stats['sentences_flagged']}")
        lines.append(f"Percentage Flagged: {stats['percentage_flagged']:.1f}%")
        lines.append("")
        
        # Thresholds
        lines.append("⚖️ THRESHOLDS")
        lines.append("─" * 80)
        lines.append(f"Good (Acceptable): < {report['thresholds']['good']:.0f}%")
        lines.append(f"Moderate (Review): {report['thresholds']['good']:.0f}% - {report['thresholds']['moderate']:.0f}%")
        lines.append(f"High (Rewrite): > {report['thresholds']['moderate']:.0f}%")
        lines.append("")
        
        # Section-wise Analysis
        if report['section_analyses']:
            lines.append("📑 SECTION-WISE ANALYSIS")
            lines.append("─" * 80)
            
            for section in report['section_analyses']:
                status_symbol = "✅" if section['status'] == 'good' else "⚠️" if section['status'] == 'moderate' else "🚨"
                
                lines.append(f"\n{status_symbol} {section['section_name'].upper()}")
                lines.append("─" * 40)
                lines.append(f"Plagiarism Score: {section['plagiarism_score']:.1f}%")
                lines.append(f"Total Sentences: {section['total_sentences']}")
                lines.append(f"Flagged Sentences: {section['sentences_flagged']}")
                lines.append(f"Status: {section['status'].upper()}")
                
                # Show flagged sentences
                if section['flagged_sentences']:
                    lines.append(f"\n🚩 Flagged Sentences ({len(section['flagged_sentences'])}):")
                    
                    for i, flagged in enumerate(section['flagged_sentences'][:5], 1):  # Show top 5
                        lines.append(f"\n  [{i}] Similarity: {flagged['similarity_score']*100:.1f}% ({flagged['severity'].upper()})")
                        lines.append(f"  Draft: {flagged['sentence'][:100]}...")
                        lines.append(f"  Source: {flagged['source_match'][:100]}...")
                        
                        # Add suggestions if available
                        if 'suggestions' in flagged:
                            lines.append(f"\n  📝 REWRITE SUGGESTIONS:")
                            for suggestion in flagged['suggestions'][:8]:  # Show key suggestions
                                lines.append(f"     {suggestion}")
                            
                            # Add rewrite strategies
                            if 'rewrite_examples' in flagged:
                                lines.append(f"\n  🔧 REWRITE STRATEGIES:")
                                for example in flagged['rewrite_examples'][:3]:
                                    lines.append(f"     • {example['strategy']}: {example['description']}")
                    
                    if len(section['flagged_sentences']) > 5:
                        lines.append(f"\n  ... and {len(section['flagged_sentences']) - 5} more flagged sentences")
        
        # Add general guidelines if suggestions were generated
        if 'suggestions_summary' in report:
            lines.append(f"\n\n📚 GENERAL REWRITING GUIDELINES")
            lines.append("─" * 80)
            for guideline in report['suggestions_summary']['general_guidelines']:
                lines.append(f"  • {guideline}")
        
        # Add external validation info if available
        if 'external_validation' in report:
            ext_val = report['external_validation']
            lines.append(f"\n\n🌐 EXTERNAL VALIDATION")
            lines.append("─" * 80)
            lines.append(f"External Checks Performed: {ext_val['checks_performed']}")
            lines.append(f"Additional Matches Found: {ext_val['matches_found']}")
            lines.append(f"API Configured: {'Yes' if ext_val['api_configured'] else 'No'}")
            if not ext_val['api_configured']:
                lines.append(f"\nNote: {ext_val['note']}")
        
        lines.append("\n" + "═" * 80)
        lines.append("End of Report")
        lines.append("═" * 80)
        
        return '\n'.join(lines)


# Test function
if __name__ == "__main__":
    print("🧪 Testing Plagiarism Detection Agent")
    print("=" * 80)
    
    # Initialize agent
    agent = PlagiarismDetectionAgent()
    
    # Test data
    test_draft = {
        'abstract': "This paper explores deep learning techniques for stock market prediction. We analyze various neural network architectures and their performance on financial time series data.",
        'introduction': "Stock market prediction has been a challenging problem in finance. Recent advances in deep learning offer new approaches to this problem.",
        'related_work': "Previous research has focused on traditional statistical methods. Deep learning approaches have shown promising results in recent years."
    }
    
    test_papers = [
        {
            'title': 'Deep Learning for Stock Prediction',
            'abstract': 'Deep learning techniques have revolutionized stock market prediction. Neural networks can capture complex patterns in financial data.'
        },
        {
            'title': 'Financial Time Series Analysis',
            'abstract': 'Time series analysis is crucial for stock market forecasting. Various statistical methods have been developed over the years.'
        }
    ]
    
    # Run plagiarism check
    report = agent.check_plagiarism(
        test_draft,
        test_papers,
        "Deep Learning for Stock Market Prediction"
    )
    
    # Generate detailed suggestions (Phase 2 feature)
    report_with_suggestions = agent.generate_detailed_suggestions(report)
    
    # Display report
    print("\n" + "=" * 80)
    print("📄 PLAGIARISM REPORT WITH DETAILED SUGGESTIONS")
    print("=" * 80)
    
    formatted_report = agent.format_report_for_export(report_with_suggestions)
    print(formatted_report)
