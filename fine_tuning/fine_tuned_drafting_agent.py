import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForSeq2SeqLM,
    pipeline
)
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import os
import re

@dataclass
class DraftingConfig:
    """Configuration for the drafting agent"""
    model_path: str = "./trained_drafting_agent"
    base_model: str = "google/flan-t5-base"
    max_new_tokens: int = 800
    min_new_tokens: int = 400
    temperature: float = 0.85
    top_p: float = 0.95
    repetition_penalty: float = 1.2
    num_beams: int = 4
    no_repeat_ngram_size: int = 3
    max_length: int = 500  # Added for Streamlit compatibility
    creativity_level: float = 0.7  # Added for Streamlit compatibility

class ContentCleaner:
    """Cleans and validates generated content"""
    
    @staticmethod
    def remove_metadata(text: str) -> str:
        """Remove publishing metadata, copyrights, contact info, etc."""
        if not text:
            return text
        
        # Remove common publishing metadata
        patterns_to_remove = [
            # Copyright and publishing info
            r'Copyright ©? \d{4} .*?\. All rights reserved\.',
            r'Published by .*? Press',
            r'Available in .*? for \$?\d+\.?\d*',
            r'ISBN: \d+-\d+-\d+-\d+',
            r'DOI: .*',
            r'arXiv:.*',
            
            # Contact/support info
            r'For confidential support.*',
            r'call .* helpline.*',
            r'visit .* website.*',
            r'email: .*@.*\..*',
            
            # Legal disclaimers
            r'This material may not be .*',
            r'No part of this .* may be .*',
            r'Any dissemination .* prohibited.*',
            r'No warranty .* given.*',
            
            # Acknowledgments and funding
            r'This work was supported by .*',
            r'We would like to thank .*',
            r'Funded by .* grant.*',
            
            # Formatting instructions
            r'Format: .*',
            r'Style: .*',
            r'Language: .*',
            r'Abstract length: .* words',
            r'This .* should be approximately .* words',
            
            # Conference/journal info
            r'In Proceedings of .*',
            r'Journal of .*, volume.*',
            r'Conference on .*',
            
            # Price and ordering info
            r'\$?\d+\.?\d* for .* copy',
            r'Available from .*',
            r'Order online at .*',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def remove_instructions(text: str) -> str:
        """Remove model instructions that appear as content"""
        instruction_patterns = [
            r'Write a .* that includes:.*',
            r'The .* should include:.*',
            r'Provide .* details about.*',
            r'Explain .* in greater depth.*',
            r'Discuss .* more thoroughly.*',
            r'Add more .* examples.*',
            r'Expand on .*',
            r'Include .* analysis.*',
            r'This .* should .*',
            r'Make sure to .*',
            r'Be sure to .*',
            r'Avoid .*',
            r'Do not .*',
        ]
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        cleaned_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if it's an instruction
            is_instruction = False
            for pattern in instruction_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    is_instruction = True
                    break
            
            if not is_instruction:
                cleaned_sentences.append(sentence)
        
        return '. '.join(cleaned_sentences) + '.'
    
    @staticmethod
    def fix_incomplete_sentences(text: str) -> str:
        """Fix incomplete/cut-off sentences"""
        # Fix common cut-off patterns
        fixes = [
            (r'(\w+), (?:a|A) (?:METH|APPROACH|RESULT|FINDING|DISCUSSION)', r'\1.'),
            (r'(\w+)\.\.\.$', r'\1.'),
            (r'(\w+)\s+$', r'\1.'),
            (r'(\w+),$', r'\1.'),
        ]
        
        for pattern, replacement in fixes:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    @staticmethod
    def clean_numbered_lists(text: str) -> str:
        """Clean up numbered lists that are cut off"""
        # Remove incomplete numbered items
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                cleaned_lines.append(line)
                continue
            
            # Check if it's a numbered item without content
            if re.match(r'^\d+\.\s*$', line) or re.match(r'^\d+\.\s*\w{1,3}$', line):
                continue  # Skip incomplete items
            
            # Check if it ends with a number (likely cut off)
            if re.match(r'.*\s+\d+\.$', line):
                line = re.sub(r'\s+\d+\.$', '.', line)
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def validate_academic_content(text: str, expected_topic: str = None) -> Tuple[bool, List[str]]:
        """Validate that text contains proper academic content and matches topic"""
        issues = []
        
        if not text or len(text.strip()) < 100:
            issues.append("Content too short (minimum 100 characters)")
            return False, issues
        
        # Check for topic relevance if expected_topic provided
        if expected_topic:
            topic_words = set(expected_topic.lower().split())
            text_lower = text.lower()
            
            # Check if at least some key words from topic appear
            matching_words = [w for w in topic_words if w in text_lower and len(w) > 3]
            if len(matching_words) == 0:
                issues.append(f"Content doesn't mention key topic: {expected_topic}")
        
        # Check for inappropriate content
        inappropriate_patterns = [
            (r'\$\d+\.\d+', "Contains pricing information"),
            (r'call\s+\d+', "Contains phone numbers"),
            (r'visit\s+.*\.com', "Contains website references"),
            (r'email:', "Contains email addresses"),
            (r'Copyright', "Contains copyright notices"),
            (r'All rights reserved', "Contains legal disclaimers"),
            (r'confidential support', "Contains support information"),
        ]
        
        for pattern, issue in inappropriate_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(issue)
        
        # Check for instructions as content
        if re.search(r'should include|must include|please include', text, re.IGNORECASE):
            issues.append("Contains instructions")
        
        # Check for proper sentence structure
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) < 3:
            issues.append("Insufficient number of sentences")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def clean_content(text: str) -> str:
        """Full cleaning pipeline"""
        if not text:
            return text
        
        # Apply all cleaning steps
        text = ContentCleaner.remove_metadata(text)
        text = ContentCleaner.remove_instructions(text)
        text = ContentCleaner.fix_incomplete_sentences(text)
        text = ContentCleaner.clean_numbered_lists(text)
        
        # Final cleanup
        text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
        text = re.sub(r'\s*([.!?])\s*', r'\1 ', text)  # Proper punctuation spacing
        text = text.strip()
        
        return text

class FineTunedDraftingAgent:  # Changed back to original class name for Streamlit compatibility
    """
    Clean drafting agent that generates valid academic content
    """
    
    def __init__(self, config: Optional[DraftingConfig] = None):
        self.config = config or DraftingConfig()
        self.tokenizer = None
        self.model = None
        self.cleaner = ContentCleaner()
        self.is_fine_tuned = False  # This is what Streamlit is looking for
        self._load_model()
    
    def _load_model(self):
        """Load model"""
        try:
            print(f"🔄 Loading model: {self.config.base_model}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.config.base_model,
                torch_dtype=torch.float32
            )
            print("✅ Model loaded successfully")
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            self.model = None
    
    def _create_clean_prompt(self, section_type: str, research_topic: str, 
                            paper_summaries: Dict, key_terms: List[str]) -> str:
        """
        Create clean prompt that is specific to the research topic and avoids problematic patterns
        """
        
        # Extract only essential information
        exec_summary = paper_summaries.get('executive_summary', '')[:400]
        insights = paper_summaries.get('key_insights', {})
        gaps = paper_summaries.get('research_gaps', [])
        
        # Clean insights - focus on relevant ones
        methods = insights.get('methodological_approaches', [])[:3]
        findings = insights.get('major_findings', [])[:3]
        
        # Build topic-specific prompts
        if section_type == "abstract":
            prompt = f"""Write a 150-200 word research abstract for: {research_topic}

Key aspects:
- Research focus: {research_topic}
- Main approaches: {', '.join(methods) if methods else 'novel techniques'}
- Significant results: {', '.join(findings) if findings else 'meaningful contributions'}
- Research challenges: {', '.join(gaps[:2]) if gaps else 'important open problems'}

Requirements:
1. Start with the research problem or motivation
2. Describe the methodology or approach used
3. Summarize the key results or findings
4. State implications and importance
5. Use clear, academic language
6. Do NOT copy from existing work

Write the abstract:"""
        
        elif section_type == "introduction":
            prompt = f"""Write an introduction section (300-400 words) for a research paper on: {research_topic}

Context:
{exec_summary}

Key research directions: {', '.join(methods) if methods else 'emerging approaches'}

Current challenges: {', '.join(gaps[:3]) if gaps else 'several important limitations'}

Requirements:
1. Begin with background and motivation for {research_topic}
2. Discuss why this research area is important
3. Identify the research gap or problem being addressed
4. State the research objectives or questions
5. Outline the paper structure
6. Use original phrasing and analysis
7. Do NOT copy from sources

Write the introduction:"""
        
        elif section_type == "related_work":
            prompt = f"""Write a related work section (400-500 words) surveying research on: {research_topic}

Field overview:
{exec_summary}

Main research approaches: {', '.join(methods) if methods else 'various methodologies'}

Key developments: {', '.join(findings) if findings else 'recent advances'}

Research gaps to address: {', '.join(gaps[:3]) if gaps else 'unresolved questions'}

Requirements:
1. Organize by themes or research approaches
2. Discuss major studies and their contributions
3. Compare different methodologies and results
4. Identify strengths and limitations of existing work
5. Highlight gaps between current research and needs
6. Synthesize ideas rather than listing papers
7. Use original analysis and connections
8. Do NOT copy sentences from papers

Write the related work section:"""
        
        else:
            prompt = f"Write about {research_topic} using the following information:\n{exec_summary}\n\nApproaches: {', '.join(methods)}\nKey findings: {', '.join(findings)}"
        
        return prompt
    
    def _generate_with_retry(self, prompt: str, research_topic: str = None, max_retries: int = 3) -> str:
        """Generate with retry and validation - use model output first"""
        for attempt in range(max_retries):
            try:
                if self.model is None:
                    print("   ⚠️ Model not loaded")
                    return ""
                
                print(f"   📝 Attempt {attempt + 1}: Sending prompt to model...")
                
                inputs = self.tokenizer(
                    prompt, 
                    return_tensors="pt", 
                    truncation=True, 
                    max_length=512
                )
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.config.max_new_tokens,
                        temperature=self.config.temperature,
                        top_p=self.config.top_p,
                        repetition_penalty=self.config.repetition_penalty,
                        num_beams=self.config.num_beams,
                        no_repeat_ngram_size=self.config.no_repeat_ngram_size,
                        do_sample=True,
                        early_stopping=True
                    )
                
                generated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                print(f"   ✍️ Raw model output length: {len(generated)} chars")
                print(f"   📄 First 100 chars: {generated[:100]}")
                
                # Aggressively remove prompt text that appears in output
                generated = generated.strip()
                
                # Remove prompt text patterns
                prompt_removal_patterns = [
                    r'^.*?(?:Write a|Write an|Write the)\s+(?:research\s+)?(?:abstract|introduction|section|related\s+work)',
                    r'^.*?(?:Key aspects|Context|Requirements|Field overview|Main research).*?:',
                    r'^\(?\d+-\d+\s+words?\)?.*?(?:\n|$)',
                    r'^.*?(?:Write|Describe|Explain|Provide|Discuss)\s+(?:a|an|the).*?:',
                ]
                
                for pattern in prompt_removal_patterns:
                    before_len = len(generated)
                    generated = re.sub(pattern, '', generated, flags=re.IGNORECASE | re.MULTILINE).strip()
                    if len(generated) < before_len:
                        print(f"   🔧 Removed prompt pattern, new length: {len(generated)}")
                
                # Clean the content
                cleaned = self.cleaner.clean_content(generated)
                print(f"   🧹 Cleaned output length: {len(cleaned)} chars")
                
                # More lenient validation - check only critical issues
                if cleaned and len(cleaned.strip()) >= 80:  # Lower minimum threshold
                    # Check for critical issues only
                    has_prices = bool(re.search(r'\$\d+', cleaned))
                    has_emails = bool(re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', cleaned))
                    has_copyright = 'copyright' in cleaned.lower()
                    
                    critical_issues = has_prices or has_emails or has_copyright
                    
                    if not critical_issues:
                        word_count = len(cleaned.split())
                        print(f"   ✅ USING MODEL OUTPUT - {word_count} words")
                        return cleaned
                    else:
                        print(f"   ⚠️ Critical issues found (prices/emails/copyright)")
                
                print(f"   ⚠️ Attempt {attempt + 1}: Content too short or invalid")
                # Adjust temperature for retry
                self.config.temperature = min(0.95, self.config.temperature + 0.1)
                    
            except Exception as e:
                print(f"   ⚠️ Generation error on attempt {attempt + 1}: {e}")
        
        print(f"   ❌ All generation attempts failed, USING FALLBACK")
        return ""  # Return empty if all attempts fail
    
    def _get_valid_fallback(self, section_type: str, research_topic: str, 
                           paper_summaries: Dict) -> str:
        """Provide valid fallback content - purely topic-based, no domain contamination"""
        
        if section_type == "abstract":
            return f"""This paper presents a comprehensive investigation of {research_topic}. We conduct a detailed analysis of current methodologies and their applications in this domain. Contemporary approaches demonstrate significant improvements over previous methods. However, several important challenges remain that require further investigation. This research contributes by synthesizing current knowledge and proposing directions for future development."""
        
        elif section_type == "introduction":
            return f"""Research on {research_topic} has received considerable attention due to its practical importance and theoretical significance. The field encompasses multiple methodological approaches, each with distinct strengths and limitations. Current work has made meaningful progress, though important challenges persist. This paper provides a comprehensive overview of the field, identifies key research gaps, and proposes promising directions for advancement. We examine how recent developments can address existing limitations."""
        
        elif section_type == "related_work":
            return f"""The field of {research_topic} has evolved substantially over recent years. Early foundational work established core concepts and fundamental principles. Subsequent research has introduced increasingly sophisticated methodologies and advanced techniques. Empirical studies demonstrate that contemporary approaches yield meaningful improvements compared to classical methods. Despite considerable progress in the field, significant challenges remain with respect to scalability, efficiency, and practical implementation in real-world scenarios. This survey synthesizes the major developments and research trends, identifies promising areas for future investigation, and discusses critical gaps that warrant further exploration."""
        
        return f"Research on {research_topic}."
    
    def generate_section(self, section_type: str, research_topic: str, 
                        paper_summaries: Dict, key_terms: List[str]) -> str:
        """Generate a clean, valid section that matches the research topic"""
        print(f"\n   🎯 Generating {section_type.upper()}...")
        
        # Create clean prompt
        prompt = self._create_clean_prompt(section_type, research_topic, paper_summaries, key_terms)
        
        # Generate with retry (pass research_topic for validation)
        content = self._generate_with_retry(prompt, research_topic=research_topic)
        
        # Check if valid
        if content:
            is_valid, issues = self.cleaner.validate_academic_content(content, expected_topic=research_topic)
            if is_valid:
                word_count = len(content.split())
                print(f"   ✅ MODEL GENERATED {word_count} valid words for {section_type}")
                return content
            else:
                print(f"   ⚠️ Model output failed validation: {issues}")
        
        # Use fallback
        fallback = self._get_valid_fallback(section_type, research_topic, paper_summaries)
        fallback_words = len(fallback.split())
        print(f"   ⚠️ USING FALLBACK - {fallback_words} words for {section_type}")
        return fallback
    
    def generate_complete_draft(self, research_topic: str, 
                               paper_summaries: Dict, 
                               key_terms: List[str]) -> Dict[str, str]:
        """Generate complete, clean draft"""
        print(f"\n{'='*60}")
        print(f"✨ GENERATING CLEAN RESEARCH DRAFT")
        print(f"   Topic: {research_topic}")
        print(f"{'='*60}\n")
        
        draft = {}
        
        # Generate sections
        sections = ["abstract", "introduction", "related_work"]
        
        for section in sections:
            content = self.generate_section(section, research_topic, paper_summaries, key_terms)
            draft[section] = content
        
        # Report
        total_words = sum(len(content.split()) for content in draft.values())
        print(f"\n{'='*60}")
        print(f"✅ DRAFT GENERATED")
        print(f"   Total words: {total_words}")
        print(f"   Sections: {len(draft)}")
        print(f"{'='*60}")
        
        return draft


def get_drafting_agent(config: Optional[DraftingConfig] = None):
    """Get clean drafting agent - KEEP ORIGINAL FUNCTION NAME"""
    return FineTunedDraftingAgent(config)  # Changed to FineTunedDraftingAgent


# Test with the problematic case
if __name__ == "__main__":
    print("="*60)
    print("CLEAN DRAFTING AGENT - TEST")
    print("="*60)
    
    config = DraftingConfig(
        base_model="google/flan-t5-base",
        max_new_tokens=600,
        temperature=0.8
    )
    
    agent = get_drafting_agent(config)
    
    # Test data similar to what caused problems
    test_summaries = {
        "executive_summary": "Deep learning for stock market prediction shows promise but has challenges.",
        "key_insights": {
            "methodological_approaches": ["LSTM networks", "CNN architectures", "hybrid models"],
            "major_findings": ["Improved accuracy over traditional methods"],
            "limitations_challenges": ["Model interpretability", "Handling extreme conditions"]
        },
        "research_gaps": ["Need for more interpretable models", "Better handling of market changes"]
    }
    
    test_topic = "Deep Learning for Stock Market Prediction"
    test_terms = ["deep learning", "stock market", "prediction"]
    
    draft = agent.generate_complete_draft(test_topic, test_summaries, test_terms)
    
    print("\n" + "="*60)
    print("CLEAN DRAFT OUTPUT:")
    print("="*60)
    
    for section, content in draft.items():
        print(f"\n{section.upper()}:")
        print("-" * 40)
        print(content[:300] + "..." if len(content) > 300 else content)
        print(f"\nWords: {len(content.split())}")