import torch
import torch.nn as nn
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling,
    DataCollatorForSeq2Seq
)
from peft import (
    get_peft_model, 
    LoraConfig, 
    TaskType,
    prepare_model_for_kbit_training
)
from datasets import Dataset
import json
from typing import Dict, List, Tuple
import os
from datetime import datetime
from core_agents.training_data_manager import TrainingDataManager
import re
from tqdm import tqdm
import numpy as np

class AcademicDatasetCreator:
    """
    Creates high-quality academic training data from research summaries
    Focuses on teaching the model academic writing patterns without copying
    """
    
    def __init__(self):
        self.data_manager = TrainingDataManager()
    
    def extract_academic_patterns(self, paper_summaries: Dict) -> Dict:
        """
        Extract academic writing patterns from summaries without copying sentences
        
        Returns:
            Dictionary of academic patterns (structure, transitions, phrasing)
        """
        patterns = {
            "section_structures": [],
            "transition_phrases": [],
            "academic_phrasing": [],
            "citation_patterns": [],
            "argument_flows": []
        }
        
        # Extract structural patterns from sections
        sections = paper_summaries.get('section_summaries', {})
        for section_name, section_content in sections.items():
            if isinstance(section_content, str) and section_content:
                # Analyze sentence structure
                sentences = re.split(r'[.!?]+', section_content)
                for sent in sentences[:20]:  # First 20 sentences
                    sent = sent.strip()
                    if len(sent.split()) > 5:  # Meaningful sentence
                        # Extract transition words
                        transitions = ["however", "furthermore", "moreover", "conversely", 
                                      "nevertheless", "therefore", "consequently", "additionally"]
                        if any(t in sent.lower() for t in transitions):
                            patterns["transition_phrases"].append(sent[:100])
                        
                        # Extract academic phrasing patterns
                        if any(p in sent.lower() for p in ["this paper", "we propose", "our approach", 
                                                          "the results show", "experiments demonstrate"]):
                            patterns["academic_phrasing"].append(sent[:150])
        
        # Extract key insights for argument patterns
        insights = paper_summaries.get('key_insights', {})
        for category, items in insights.items():
            if items and isinstance(items, list):
                for item in items[:5]:
                    if isinstance(item, str):
                        # Extract argument structure
                        if "demonstrate" in item.lower() or "show" in item.lower():
                            patterns["argument_flows"].append(item)
        
        return patterns
    
    def create_learning_examples(self, research_project: Dict) -> List[Tuple[str, str]]:
        """
        Create input-output pairs for training where model learns to generate
        original content inspired by patterns, not copied text
        
        Args:
            research_project: Complete research project data
            
        Returns:
            List of (prompt, original_content) pairs
        """
        examples = []
        topic = research_project["research_topic"]
        
        # Get comprehensive summary (our source of learning)
        paper_summaries = research_project.get("paper_summaries", {})
        if not paper_summaries:
            return examples
        
        # Extract academic patterns
        patterns = self.extract_academic_patterns(paper_summaries)
        
        # Create section-specific learning examples
        draft_sections = research_project.get("draft", {})
        
        # Abstract learning
        if draft_sections.get("abstract"):
            # Create prompt that asks for abstract inspired by patterns
            prompt = self._create_abstract_prompt(topic, patterns, paper_summaries)
            examples.append((prompt, draft_sections["abstract"]))
        
        # Introduction learning  
        if draft_sections.get("introduction"):
            prompt = self._create_introduction_prompt(topic, patterns, paper_summaries)
            examples.append((prompt, draft_sections["introduction"]))
        
        # Related work learning
        if draft_sections.get("related_work"):
            prompt = self._create_related_work_prompt(topic, patterns, paper_summaries)
            examples.append((prompt, draft_sections["related_work"]))
        
        return examples
    
    def _create_abstract_prompt(self, topic: str, patterns: Dict, paper_summaries: Dict) -> str:
        """Create prompt for abstract generation"""
        key_terms = paper_summaries.get('metadata', {}).get('keywords', [])[:5]
        
        prompt = f"""Write an ORIGINAL abstract for a research paper on: {topic}

Key terms to incorporate: {', '.join(key_terms)}

Academic patterns to emulate (DO NOT COPY, use as inspiration):
- {patterns.get('academic_phrasing', ['Academic writing style'])[0] if patterns.get('academic_phrasing') else 'Professional academic tone'}
- {patterns.get('transition_phrases', ['Logical flow'])[0] if patterns.get('transition_phrases') else 'Coherent argument structure'}

Core research directions from literature:
{paper_summaries.get('executive_summary', '')[:300]}

Write a novel abstract that:
1. States the research problem
2. Describes the approach/methodology
3. Summarizes key findings
4. Mentions implications

Abstract:"""
        return prompt
    
    def _create_introduction_prompt(self, topic: str, patterns: Dict, paper_summaries: Dict) -> str:
        """Create prompt for introduction generation"""
        research_context = paper_summaries.get('section_summaries', {}).get(
            'Research Context and Background', 
            'Background context from existing literature'
        )[:400]
        
        prompt = f"""Write an ORIGINAL introduction for a research paper on: {topic}

Research Context (use as background, do not copy):
{research_context}

Academic writing patterns to follow:
{self._format_patterns_for_learning(patterns)}

Key insights from literature review:
{self._format_insights_for_learning(paper_summaries.get('key_insights', {}))}

Write a novel introduction that:
1. Provides background and motivation
2. States the research gap
3. Presents research questions/objectives
4. Outlines paper structure

Introduction:"""
        return prompt
    
    def _create_related_work_prompt(self, topic: str, patterns: Dict, paper_summaries: Dict) -> str:
        """Create prompt for related work generation"""
        # Get synthesized view rather than individual papers
        synthesis = paper_summaries.get('synthesis', 'Synthesized view of existing research')
        
        prompt = f"""Write an ORIGINAL related work section for a research paper on: {topic}

Synthesized Research Landscape (use as conceptual framework):
{synthesis}

Academic citation patterns to emulate:
{self._extract_citation_patterns(patterns)}

Research Gaps Identified:
{chr(10).join(paper_summaries.get('research_gaps', ['Research gaps in the field']))}

Write a novel related work section that:
1. Categorizes existing approaches thematically
2. Critically analyzes strengths/limitations
3. Identifies research gaps
4. Positions your work within the literature

Related Work:"""
        return prompt
    
    def _format_patterns_for_learning(self, patterns: Dict) -> str:
        """Format patterns for learning prompts"""
        formatted = []
        for category, items in patterns.items():
            if items and len(items) > 0:
                formatted.append(f"- {category}: {items[0][:100]}")
        return '\n'.join(formatted[:3])
    
    def _format_insights_for_learning(self, insights: Dict) -> str:
        """Format insights for learning prompts"""
        formatted = []
        for category, items in insights.items():
            if items and isinstance(items, list) and len(items) > 0:
                formatted.append(f"- {category}: {items[0]}")
        return '\n'.join(formatted[:4])
    
    def _extract_citation_patterns(self, patterns: Dict) -> str:
        """Extract and format citation patterns"""
        if patterns.get("citation_patterns"):
            return "\n".join([f"- {p}" for p in patterns["citation_patterns"][:3]])
        return "- Academic citation style: (Author et al., Year) found that..."


class DraftingAgentTrainer:
    """
    Fine-tunes a language model for ORIGINAL research paper drafting
    Trains on patterns from summaries, not copied text
    """
    
    def __init__(self, model_name: str = "google/flan-t5-base"):
        """
        Initialize trainer with instruction-tuned base model
        
        Args:
            model_name: Hugging Face model identifier (T5 is better for text-to-text)
        """
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.lora_config = None
        self.data_manager = TrainingDataManager()
        self.dataset_creator = AcademicDatasetCreator()
        
    def setup_model(self):
        """Initialize model and tokenizer with LoRA configuration"""
        
        print(f"🔄 Loading instruction-tuned model: {self.model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.tokenizer.padding_side = "right"
        
        # Load model - T5 is better for instruction following
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True
        )
        
        # Configure LoRA for better academic text generation
        self.lora_config = LoraConfig(
            task_type=TaskType.SEQ_2_SEQ_LM,
            inference_mode=False,
            r=32,  # Higher rank for complex academic text
            lora_alpha=64,
            lora_dropout=0.1,
            bias="none",
            target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        )
        
        # Prepare model for training
        self.model = get_peft_model(self.model, self.lora_config)
        
        print(f"✅ Model setup complete with LoRA")
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"   Trainable: {trainable_params:,}/{total_params:,} ({trainable_params/total_params:.2%})")
    
    def create_pattern_based_training_data(self) -> List[Dict[str, str]]:
        """
        Create training data focused on academic patterns, not copied text
        Each sample teaches the model how to write originally based on patterns
        """
        
        training_samples = []
        collected_data = self.data_manager.training_data
        
        print(f"📚 Creating pattern-based training from {len(collected_data)} research projects...")
        
        for idx, research_project in enumerate(collected_data):
            # Get learning examples (prompt, original_content)
            examples = self.dataset_creator.create_learning_examples(research_project)
            
            for prompt, content in examples:
                # Ensure content is original (not directly copied from sources)
                if self._is_original_content(content, research_project):
                    training_samples.append({
                        "instruction": prompt,
                        "input": "",
                        "output": content
                    })
            
            print(f"   ✅ Project {idx+1}: Learned patterns from '{research_project['research_topic'][:50]}...'")
        
        print(f"📊 Total pattern-based training samples: {len(training_samples)}")
        return training_samples
    
    def _is_original_content(self, content: str, research_project: Dict) -> bool:
        """
        Check if content appears to be original (not directly copied)
        Simple heuristic-based check
        """
        # Get all source text from the research project
        all_source_text = ""
        
        # Add query analysis text
        query_data = research_project.get("query_analysis", {})
        all_source_text += str(query_data.get("keywords", [])) + " "
        all_source_text += str(query_data.get("subtopics", [])) + " "
        
        # Add paper summaries text
        paper_summaries = research_project.get("paper_summaries", {})
        if isinstance(paper_summaries, dict):
            for key, value in paper_summaries.items():
                if isinstance(value, str):
                    all_source_text += value + " "
                elif isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, str):
                            all_source_text += subvalue + " "
        
        # Check for direct copying (long exact matches)
        words = content.split()
        if len(words) < 30:
            return False  # Too short to be meaningful
        
        # Check for consecutive word matches (5+ consecutive words)
        content_lower = content.lower()
        source_lower = all_source_text.lower()
        
        # Simple n-gram check for copying
        for i in range(len(words) - 4):
            ngram = ' '.join(words[i:i+5]).lower()
            if ngram in source_lower and len(ngram) > 20:
                return False  # Found copied n-gram
        
        return True
    
    def prepare_dataset(self) -> Dataset:
        """Prepare dataset from pattern-based training data"""
        
        # Create training data focused on patterns
        training_data = self.create_pattern_based_training_data()
        
        if not training_data:
            raise ValueError("❌ No valid training data available. Complete some research projects first!")
        
        # Tokenize function for instruction tuning
        def tokenize_function(examples):
            # Format: Instruction + Input -> Output
            prompts = [f"{example['instruction']} {example['input']}" for example in examples]
            targets = examples["output"]
            
            # Tokenize inputs
            model_inputs = self.tokenizer(
                prompts,
                truncation=True,
                padding="max_length",
                max_length=512,
                return_tensors=None
            )
            
            # Tokenize targets
            labels = self.tokenizer(
                targets,
                truncation=True,
                padding="max_length",
                max_length=512,
                return_tensors=None
            )
            
            model_inputs["labels"] = labels["input_ids"]
            return model_inputs
        
        # Create dataset
        dataset = Dataset.from_list(training_data)
        tokenized_dataset = dataset.map(
            tokenize_function, 
            batched=True,
            remove_columns=["instruction", "input", "output"]
        )
        
        print(f"✅ Pattern-based dataset prepared: {len(tokenized_dataset)} samples")
        return tokenized_dataset
    
    def train(self, output_dir: str = "./trained_drafting_agent", epochs: int = 5):
        """
        Fine-tune the model on academic patterns from real research
        
        Args:
            output_dir: Directory to save trained model
            epochs: Number of training epochs
        """
        
        # Check if we have enough pattern-based data
        if not self.data_manager.prepare_for_fine_tuning(min_samples=3):
            raise ValueError(
                f"❌ Not enough training data. Need at least 3 research projects. "
                f"Current: {len(self.data_manager.training_data)}"
            )
        
        print("="*60)
        print("🚀 STARTING PATTERN-BASED FINE-TUNING")
        print("Model learns to write originally from academic patterns")
        print("="*60)
        
        # Setup model
        self.setup_model()
        
        # Prepare pattern-based dataset
        dataset = self.prepare_dataset()
        
        # Training arguments for academic text generation
        training_args = TrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=100,
            logging_steps=20,
            save_steps=200,
            learning_rate=3e-4,  # Higher for pattern learning
            fp16=torch.cuda.is_available(),
            optim="adamw_torch",
            report_to=None,
            save_total_limit=2,
            remove_unused_columns=True,
            gradient_checkpointing=True,
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            evaluation_strategy="no",
            save_strategy="epoch",
            load_best_model_at_end=False,
            metric_for_best_model="loss",
            greater_is_better=False,
        )
        
        # Data collator for seq2seq
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model,
            padding=True
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
        )
        
        # Start training
        print(f"\n🎯 Training on {len(dataset)} pattern-based samples")
        print(f"📊 From {len(self.data_manager.training_data)} research projects")
        print(f"🔥 Training for {epochs} epochs...\n")
        
        trainer.train()
        
        # Save model
        print("\n💾 Saving trained model...")
        trainer.save_model()
        self.tokenizer.save_pretrained(output_dir)
        self.model.config.save_pretrained(output_dir)
        
        print(f"✅ Training complete! Model saved to {output_dir}")
        
        # Save detailed training metadata
        stats = self.data_manager.get_training_statistics()
        training_metadata = {
            "training_date": datetime.now().isoformat(),
            "training_strategy": "pattern_based_original_generation",
            "training_samples": len(dataset),
            "research_projects": len(self.data_manager.training_data),
            "model_base": self.model_name,
            "epochs": epochs,
            "learning_rate": 3e-4,
            "lora_config": {
                "r": self.lora_config.r,
                "alpha": self.lora_config.lora_alpha,
                "dropout": self.lora_config.lora_dropout
            },
            "data_sources": [d["research_topic"] for d in self.data_manager.training_data],
            "statistics": stats,
            "notes": "Model trained to generate original academic text based on patterns extracted from research summaries, not to copy existing text."
        }
        
        with open(os.path.join(output_dir, "training_metadata.json"), "w") as f:
            json.dump(training_metadata, f, indent=2)
        
        # Calculate and save training metrics
        training_metrics = {
            "final_loss": trainer.state.log_history[-1]["loss"] if trainer.state.log_history else None,
            "total_training_steps": trainer.state.max_steps,
            "pattern_learning_samples": len(dataset),
            "originality_check": "enabled"
        }
        
        with open(os.path.join(output_dir, "training_metrics.json"), "w") as f:
            json.dump(training_metrics, f, indent=2)
        
        print("\n" + "="*60)
        print("🎉 PATTERN-BASED FINE-TUNING COMPLETED!")
        print("Model learns to write originally from academic patterns")
        print("="*60)
        
        return output_dir


def auto_train_if_ready(min_samples: int = 3):
    """
    Automatically train if enough pattern-based data is available
    
    Args:
        min_samples: Minimum samples required for training
        
    Returns:
        True if training was performed, False otherwise
    """
    data_manager = TrainingDataManager()
    
    if data_manager.prepare_for_fine_tuning(min_samples=min_samples):
        print(f"\n🎯 {len(data_manager.training_data)} research projects analyzed!")
        print("🚀 Extracting academic patterns for training...")
        print("✨ Starting automatic pattern-based fine-tuning...")
        
        trainer = DraftingAgentTrainer(model_name="google/flan-t5-large")  # Larger model for better quality
        trainer.train(epochs=7)  # More epochs for pattern learning
        return True
    else:
        stats = data_manager.get_training_statistics()
        print(f"\n📊 Training data status:")
        print(f"   Projects analyzed: {stats['total_samples']}/{min_samples}")
        print(f"   Pattern samples: {stats.get('pattern_samples', 0)}")
        print(f"   Topics covered: {stats['topics_covered']}")
        return False


# Test/Demo function
if __name__ == "__main__":
    print("="*60)
    print("PATTERN-BASED DRAFTING AGENT TRAINER")
    print("Learns academic writing patterns, not copies text")
    print("="*60)
    
    # Check training readiness
    print("\n📋 Checking pattern data availability...")
    
    if auto_train_if_ready(min_samples=3):
        print("\n✅ Pattern-based training completed!")
        print("   Model now generates original academic text based on learned patterns")
    else:
        print("\n⏳ Not enough patterns collected yet.")
        print("💡 Complete more research projects to extract academic writing patterns.")