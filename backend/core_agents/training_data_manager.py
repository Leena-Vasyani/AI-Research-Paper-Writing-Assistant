import json
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd

class TrainingDataManager:
    """
    Manages collection and preparation of training data from retrieved papers
    """
    
    def __init__(self, data_file: str = "training_data.json"):
        self.data_file = data_file
        self.training_data = self._load_existing_data()
    
    def _load_existing_data(self) -> List[Dict]:
        """Load existing training data from file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📚 Loaded {len(data)} existing training samples")
                    return data
            except Exception as e:
                print(f"⚠️ Error loading training data: {e}")
                return []
        return []
    
    def save_training_data(self):
        """Save training data to file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(self.training_data)} training samples")
        except Exception as e:
            print(f"⚠️ Error saving training data: {e}")
    
    def create_training_sample(self, research_topic: str, query_result: Dict, 
                             paper_summaries: List[Dict], generated_draft: Dict) -> Dict:
        """
        Create a training sample from completed research cycle
        
        Args:
            research_topic: Original research topic
            query_result: Keywords and analysis from query agent
            paper_summaries: Summaries from summarization agent
            generated_draft: Generated draft sections
            
        Returns:
            Training sample dictionary
        """
        
        training_sample = {
            "research_topic": research_topic,
            "timestamp": datetime.now().isoformat(),
            "keywords": query_result.get("keywords", []),
            "reference_summaries": [],
            "abstract": generated_draft.get("abstract", ""),
            "introduction": generated_draft.get("introduction", ""),
            "related_work": generated_draft.get("related_work", ""),
            "metadata": {
                "num_references": len(paper_summaries),
                "source_papers": [s.get("title", "") for s in paper_summaries],
                "complexity": query_result.get("complexity_analysis", {})
            }
        }
        
        # Add reference summaries (the actual papers used)
        for summary in paper_summaries:
            training_sample["reference_summaries"].append({
                "title": summary.get("title", ""),
                "abstract": summary.get("concise_summary", ""),
                "full_abstract": summary.get("full_abstract", ""),
                "sections": summary.get("sections", {}),
                "confidence": summary.get("confidence", 0.0),
                "matched_keywords": summary.get("matched_keywords", [])
            })
        
        return training_sample
    
    def add_completed_research(self, research_topic: str, query_result: Dict,
                             paper_summaries: List[Dict], generated_draft: Dict):
        """
        Add a completed research project to training data
        
        Args:
            research_topic: Original research topic
            query_result: Results from query agent
            paper_summaries: Paper summaries
            generated_draft: Generated draft sections
        """
        
        if not isinstance(paper_summaries, list):
            print("⚠️ Skipping training data: paper_summaries is not a list")
            return

        paper_summaries = [s for s in paper_summaries if isinstance(s, dict)]
        if not paper_summaries:
            print("⚠️ Skipping training data: no valid paper summaries")
            return

        # Quality filter: only add samples with good confidence scores
        high_quality_summaries = [
            s for s in paper_summaries
            if s.get('confidence', 0) > 0.6
        ]
        
        if len(high_quality_summaries) >= 2:  # Minimum 2 good papers
            sample = self.create_training_sample(
                research_topic, query_result, high_quality_summaries, generated_draft
            )
            self.training_data.append(sample)
            self.save_training_data()
            print(f"✅ Added training sample: {research_topic}")
            print(f"   Total samples: {len(self.training_data)}")
        else:
            print(f"⚠️ Skipped low-quality sample: {research_topic}")
            print(f"   Only {len(high_quality_summaries)} high-confidence papers")
    
    def get_training_statistics(self) -> Dict:
        """Get statistics about collected training data"""
        if not self.training_data:
            return {
                "total_samples": 0,
                "total_references": 0,
                "topics_covered": 0,
                "latest_addition": None,
                "avg_references_per_sample": 0
            }
        
        total_refs = sum(len(sample["reference_summaries"]) 
                        for sample in self.training_data)
        
        return {
            "total_samples": len(self.training_data),
            "total_references": total_refs,
            "topics_covered": len(set(sample["research_topic"] 
                                    for sample in self.training_data)),
            "latest_addition": self.training_data[-1]["timestamp"] if self.training_data else None,
            "avg_references_per_sample": total_refs / len(self.training_data) if self.training_data else 0
        }
    
    def prepare_for_fine_tuning(self, min_samples: int = 3) -> bool:
        """
        Check if we have enough data for fine-tuning
        
        Args:
            min_samples: Minimum number of samples required
            
        Returns:
            True if ready for training, False otherwise
        """
        ready = len(self.training_data) >= min_samples
        
        if ready:
            print(f"✅ Ready for fine-tuning with {len(self.training_data)} samples")
        else:
            print(f"⏳ Need {min_samples - len(self.training_data)} more samples for training")
        
        return ready
    
    def export_training_data(self, output_file: str = "training_export.json"):
        """Export training data to a separate file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_data, f, indent=2, ensure_ascii=False)
            print(f"📤 Exported training data to {output_file}")
        except Exception as e:
            print(f"⚠️ Error exporting data: {e}")
    
    def clear_training_data(self):
        """Clear all training data (use with caution!)"""
        self.training_data = []
        self.save_training_data()
        print("🗑️ Training data cleared")


# Test function
if __name__ == "__main__":
    manager = TrainingDataManager()
    
    # Test with sample data
    test_topic = "Machine Learning in Medical Imaging"
    test_query = {
        "keywords": ["machine learning", "medical imaging", "diagnosis"],
        "complexity_analysis": {"estimated_complexity": "medium"}
    }
    test_summaries = [
        {
            "title": "Deep Learning for Medical Image Analysis",
            "concise_summary": "This paper presents deep learning methods for medical imaging.",
            "confidence": 0.85,
            "matched_keywords": ["machine learning", "medical imaging"]
        }
    ]
    test_draft = {
        "abstract": "This research explores machine learning applications in medical imaging...",
        "introduction": "Medical imaging has been transformed by machine learning...",
        "related_work": "Previous work in this area includes..."
    }
    
    manager.add_completed_research(test_topic, test_query, test_summaries, test_draft)
    
    stats = manager.get_training_statistics()
    print(f"\n📊 Training Statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")