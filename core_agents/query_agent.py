import numpy as np
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List

class ScientificQueryAgent:
    """
    Extracts keywords and analyzes research topics using SciBERT
    """
    
    def __init__(self):
        print("🔄 Loading SciBERT model for query analysis...")
        try:
            # Use SciBERT for scientific accuracy
            self.model = SentenceTransformer("allenai/scibert_scivocab_uncased")
            self.kw_model = KeyBERT(model=self.model)
            print("✅ SciBERT model loaded successfully")
        except Exception as e:
            print(f"⚠️ Error loading SciBERT: {e}")
            print("🔄 Falling back to all-MiniLM model...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.kw_model = KeyBERT(model=self.model)

    def extract_keywords(self, text: str, top_n: int = 8) -> List[str]:
        """
        Extract key scientific phrases using KeyBERT + SciBERT
        
        Args:
            text: Research topic or query text
            top_n: Number of keywords to extract
            
        Returns:
            List of extracted keywords
        """
        try:
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),  # single to 3-word phrases
                stop_words='english',
                top_n=top_n,
                use_maxsum=True,    # reduce redundancy
                nr_candidates=20,
                diversity=0.7  # Increase diversity of keywords
            )
            return [kw for kw, score in keywords]
        except Exception as e:
            print(f"⚠️ Error extracting keywords: {e}")
            # Fallback: simple word extraction
            words = text.lower().split()
            return list(set(words))[:top_n]

    def expand_keywords(self, keywords: List[str], top_n: int = 3) -> Dict[str, List[str]]:
        """
        Expand keywords into related concepts using embeddings similarity
        
        Args:
            keywords: List of main keywords
            top_n: Number of related concepts per keyword
            
        Returns:
            Dictionary mapping each keyword to related concepts
        """
        if not keywords or len(keywords) < 2:
            return {kw: [] for kw in keywords}

        try:
            embeddings = self.model.encode(keywords)
            subtopics = {}
            
            for idx, kw in enumerate(keywords):
                # Compute cosine similarity to all other keywords
                sims = cosine_similarity([embeddings[idx]], embeddings)[0]
                # Get top related indices (skip itself)
                related_idx = np.argsort(sims)[::-1][1:top_n+1]
                subtopics[kw] = [keywords[i] for i in related_idx if i < len(keywords)]
            
            return subtopics
        except Exception as e:
            print(f"⚠️ Error expanding keywords: {e}")
            return {kw: keywords[:top_n] for kw in keywords}

    def analyze_topic_complexity(self, text: str) -> Dict[str, any]:
        """
        Analyze the complexity and breadth of the research topic
        """
        words = text.split()
        word_count = len(words)
        
        # Simple complexity metrics
        complexity = {
            "word_count": word_count,
            "estimated_complexity": "high" if word_count > 10 else "medium" if word_count > 5 else "low",
            "is_specific": word_count > 5,
            "recommended_papers": 5 if word_count > 8 else 7 if word_count > 5 else 10
        }
        
        return complexity

    def run(self, text: str, top_keywords: int = 8) -> Dict:
        """
        Complete query analysis pipeline
        
        Args:
            text: Research topic
            top_keywords: Number of keywords to extract
            
        Returns:
            Dictionary with keywords, subtopics, and analysis
        """
        print(f"🔍 Analyzing topic: '{text}'")
        
        # Extract keywords
        keywords = self.extract_keywords(text, top_n=top_keywords)
        print(f"✅ Extracted {len(keywords)} keywords")
        
        # Expand to subtopics
        subtopics = self.expand_keywords(keywords, top_n=3)
        print(f"✅ Mapped {len(subtopics)} subtopics")
        
        # Analyze complexity
        complexity = self.analyze_topic_complexity(text)
        
        return {
            "original_topic": text,
            "keywords": keywords,
            "subtopics": subtopics,
            "complexity_analysis": complexity
        }


# Test function
if __name__ == "__main__":
    agent = ScientificQueryAgent()
    
    # Test with sample topic
    test_topic = "Applications of Large Language Models in Healthcare Diagnostics"
    
    print("\n" + "="*60)
    result = agent.run(test_topic, top_keywords=8)
    
    print("\n📋 Query Analysis Results:")
    print(f"Topic: {result['original_topic']}")
    print(f"\n🔑 Keywords ({len(result['keywords'])}):")
    for i, kw in enumerate(result['keywords'], 1):
        print(f"  {i}. {kw}")
    
    print(f"\n🗺️ Subtopics:")
    for main, subs in list(result['subtopics'].items())[:3]:
        print(f"  {main}: {', '.join(subs)}")
    
    print(f"\n📊 Complexity: {result['complexity_analysis']['estimated_complexity']}")
    print(f"   Recommended papers: {result['complexity_analysis']['recommended_papers']}")