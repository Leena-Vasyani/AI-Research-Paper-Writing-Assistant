from typing import Dict, List, Optional
import random


class ResearchQuestionsAgent:
    """
    Generate research questions based on a user query or the output of
    `ScientificQueryAgent`.

    Expected input (preferably): a dict with keys:
      - `original_topic` (str)
      - `keywords` (List[str])
      - `subtopics` (Dict[str, List[str]])
      - `complexity_analysis` (Dict)

    The `run` method returns a dictionary with generated questions and a
    category grouping to help downstream UI or workflows.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        random.seed(seed)

    def _sanitize_keywords(self, keywords: List[str]) -> List[str]:
        if not keywords:
            return []
        # Deduplicate while preserving order and strip whitespace
        seen = set()
        out = []
        for kw in keywords:
            k = kw.strip()
            if not k:
                continue
            if k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
        return out

    def _keyword_questions(self, topic: str, keywords: List[str]) -> List[str]:
        qs = []
        for kw in keywords:
            qs.append(f"What is the precise role of {kw} in {topic}?")
            qs.append(f"How does {kw} interact with other core concepts in {topic}?")
            qs.append(f"What are the main limitations of current approaches using {kw} for {topic}?")
        return qs

    def _subtopic_questions(self, main: str, subs: List[str], topic: str) -> List[str]:
        qs = []
        if not subs:
            return qs
        # Comparative and integrative questions
        for s in subs:
            qs.append(f"How does {s} compare to {main} when addressing aspects of {topic}?")
            qs.append(f"Can methods from {s} be combined with {main} to improve results for {topic}?")
        # Cross-subtopic synthesis
        if len(subs) > 1:
            pair = random.sample(subs, 2)
            qs.append(f"What insights arise by synthesizing {pair[0]} and {pair[1]} for {topic}?")
        return qs

    def _methodology_questions(self, topic: str, complexity: Dict) -> List[str]:
        qs = [
            f"What datasets are most appropriate to study {topic}, and why?",
            f"What evaluation metrics best capture progress on {topic}?",
            f"What experimental controls are necessary to ensure reproducibility when researching {topic}?",
            f"Which modeling or algorithmic families are promising for {topic}, and what are their trade-offs?",
        ]

        if complexity and complexity.get("estimated_complexity") == "high":
            qs.append(f"Given the high complexity, what modularization strategies reduce experimental cost for {topic}?")

        return qs

    def _ethics_and_impact(self, topic: str) -> List[str]:
        return [
            f"What are the potential ethical or societal impacts of advances in {topic}?",
            f"Are there bias or fairness concerns specific to {topic} that must be addressed?",
            f"What safety or privacy risks arise when deploying systems related to {topic}?",
        ]

    def _future_and_open(self, topic: str) -> List[str]:
        return [
            f"What are the most important open problems in {topic}?",
            f"Which adjacent fields could be leveraged to accelerate progress on {topic}?",
            f"What metrics or benchmarks would meaningfully move the field of {topic} forward?",
        ]

    def run(
        self,
        topic: str,
        query_agent_output: Optional[Dict] = None,
        num_questions: int = 12,
    ) -> Dict:
        """
        Generate a set of research questions.

        Args:
            topic: user-provided topic string (fallback if query_agent_output is None)
            query_agent_output: optional dict output from `ScientificQueryAgent`
            num_questions: maximum number of questions to return

        Returns:
            Dict containing `topic`, `questions` (list), and `by_category` mapping.
        """
        # Prefer structured data if provided
        qa = query_agent_output or {}
        orig = qa.get("original_topic", topic) if isinstance(qa, dict) else topic
        keywords = self._sanitize_keywords(qa.get("keywords", [])) if isinstance(qa, dict) else []
        subtopics = qa.get("subtopics", {}) if isinstance(qa, dict) else {}
        complexity = qa.get("complexity_analysis", {}) if isinstance(qa, dict) else {}

        questions = []
        by_category: Dict[str, List[str]] = {}

        # Generate keyword-focused questions
        kw_qs = self._keyword_questions(orig, keywords[:6])
        by_category["keyword_focused"] = kw_qs
        questions.extend(kw_qs)

        # Generate subtopic questions
        st_qs = []
        for main, subs in list(subtopics.items())[:6]:
            st_qs.extend(self._subtopic_questions(main, subs, orig))
        by_category["subtopic_focused"] = st_qs
        questions.extend(st_qs)

        # Methodology, ethics, future
        meth = self._methodology_questions(orig, complexity)
        ethics = self._ethics_and_impact(orig)
        future = self._future_and_open(orig)

        by_category["methodology"] = meth
        by_category["ethics_and_impact"] = ethics
        by_category["future_and_open"] = future

        questions.extend(meth)
        questions.extend(ethics)
        questions.extend(future)

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for q in questions:
            key = q.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(q)

        # Trim to requested size
        if len(deduped) > num_questions:
            deduped = deduped[:num_questions]

        return {
            "topic": orig,
            "questions": deduped,
            "by_category": {k: v for k, v in by_category.items()}
        }


if __name__ == "__main__":
    # Simple local test
    qa_output = {
        "original_topic": "Applications of Large Language Models in Healthcare Diagnostics",
        "keywords": ["large language models", "healthcare diagnostics", "clinical decision support", "EHR integration"],
        "subtopics": {
            "large language models": ["fine-tuning", "prompt engineering"],
            "healthcare diagnostics": ["radiology", "pathology"]
        },
        "complexity_analysis": {"estimated_complexity": "high"}
    }

    agent = ResearchQuestionsAgent()
    out = agent.run(topic=qa_output["original_topic"], query_agent_output=qa_output, num_questions=15)
    print("\nGenerated Research Questions:\n")
    for i, q in enumerate(out["questions"], 1):
        print(f"{i}. {q}")
