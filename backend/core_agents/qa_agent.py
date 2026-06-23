"""
Q&A Agent — derive the *research-grade* questions a body of literature raises,
then answer them grounded in the retrieved papers.

Position in the pipeline (between Topic Mining and Outline):

    search -> topic_mining -> qa -> outline -> drafting -> ...

Given the user query (``topic``) and the fetched ``corpus`` (plus the mined
``themes``/gaps from Topic Mining), this agent:

  1. Generates a small set of **research-level** questions — the kind a senior
     scientist / principal researcher / senior architect would raise: open
     problems, contradictions across papers, methodological limitations,
     scalability / generalization / failure modes, untested assumptions,
     trade-offs, falsifiable hypotheses. NOT shallow "what is X" questions.
  2. For each question, retrieves the most relevant papers (FAISS if available,
     else lexical — mirroring DraftingAgent) and answers strictly from them,
     recording which source titles grounded the answer.

The Drafting Agent injects these Q&A pairs into the Introduction and
Related-Work / lit-review sections so the prose is grounded in concrete,
source-backed answers.

Generation uses the large model tier (Ollama -> Groq -> Gemini). It degrades
gracefully to a deterministic, gap-oriented heuristic when no LLM is available,
so the pipeline always yields a usable Q&A artifact offline.

Returns (consumed by the drafting node and the /api/qa endpoint):

    {
      "questions": ["...", ...],
      "qa_pairs": [
        {"question": "...", "answer": "...", "sources": ["<paper title>", ...]},
        ...
      ],
      "method": "llm" | "heuristic",
    }
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

try:
    from backend.core_agents.search_agent import _get_embed_model
except Exception:  # pragma: no cover
    _get_embed_model = lambda: None  # type: ignore[assignment]


_MAX_QUESTIONS = int(os.getenv("QA_MAX_QUESTIONS", "6"))
_REFS_PER_QUESTION = int(os.getenv("QA_REFS_PER_QUESTION", "4"))


class QAAgent:
    def __init__(self, use_llm: bool = True, max_questions: int = _MAX_QUESTIONS):
        self.use_llm = use_llm
        self.max_questions = max_questions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        topic: str,
        corpus: List[Dict[str, Any]],
        *,
        themes: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        topic = (topic or "").strip()
        corpus = corpus or []
        themes = themes or {}
        constraints = constraints or {}
        n = int(constraints.get("max_questions") or self.max_questions)

        if not topic and not corpus:
            return {"questions": [], "qa_pairs": [], "method": "heuristic"}

        index = self._build_index(corpus)

        # 1. Research-grade questions.
        questions: List[str] = []
        if self.use_llm and self._llm_available():
            questions = self._llm_questions(topic, corpus, themes, n)
        if not questions:
            questions = self._heuristic_questions(topic, themes, n)
        questions = questions[:n]

        # 2. Grounded answers, one per question.
        used_llm_answer = False
        qa_pairs: List[Dict[str, Any]] = []
        for q in questions:
            refs = self._retrieve_refs(q, corpus, index)
            answer = ""
            if self.use_llm and self._llm_available():
                answer = self._llm_answer(q, refs, topic) or ""
                if answer:
                    used_llm_answer = True
            if not answer:
                answer = self._heuristic_answer(q, refs, topic)
            qa_pairs.append(
                {
                    "question": q,
                    "answer": answer,
                    "sources": [r.get("title", "") for r in refs if r.get("title")],
                }
            )

        method = "llm" if (self.use_llm and self._llm_available() and (questions and used_llm_answer)) else "heuristic"
        return {"questions": questions, "qa_pairs": qa_pairs, "method": method}

    # ------------------------------------------------------------------
    # LLM availability
    # ------------------------------------------------------------------

    def _llm_available(self) -> bool:
        if not self.use_llm:
            return False
        try:
            from backend.core_agents.llm_provider import active_providers
            return bool(active_providers())
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    def _llm_questions(
        self, topic: str, corpus: List[Dict[str, Any]], themes: Dict[str, Any], n: int
    ) -> List[str]:
        try:
            from backend.runtime.models import large_model
        except Exception:
            return []

        titles = "\n".join(
            f"- {p.get('title','')}: {(p.get('abstract','') or '')[:200]}"
            for p in corpus[:12]
        ) or "(no papers retrieved)"
        gaps = "; ".join(map(str, (themes.get("gaps") or [])[:8]))
        taxonomy = ", ".join(map(str, (themes.get("taxonomy") or [])[:8]))

        system = (
            "You are a principal research scientist and senior software architect "
            "chairing a paper's framing discussion. You ask sharp, research-level "
            "questions — the kind that expose open problems and shape a contribution. "
            "You never ask shallow, encyclopedic, or definitional questions."
        )
        prompt = (
            f"Topic: \"{topic}\"\n"
            f"Mined themes: {taxonomy or '(none)'}\n"
            f"Identified gaps: {gaps or '(none)'}\n"
            f"Retrieved literature:\n{titles}\n\n"
            f"Generate exactly {n} RESEARCH-LEVEL questions that this body of work "
            f"raises. Each question MUST probe at least one of: unresolved research "
            f"gaps / open problems, contradictions or disagreements ACROSS the papers, "
            f"methodological limitations or validity threats, scalability / "
            f"generalization / failure modes, untested assumptions, trade-offs, or "
            f"falsifiable hypotheses and future directions. Ground each question in "
            f"tensions actually visible in the literature and gaps above.\n\n"
            f"STRONG examples (emulate these):\n"
            f"- \"Do the reported efficiency gains hold under distribution shift, or "
            f"do prior evaluations conflate in-domain accuracy with robustness?\"\n"
            f"- \"The surveyed methods disagree on whether sparsity or quantization "
            f"dominates the latency budget — what experimental confound explains the "
            f"contradiction?\"\n"
            f"WEAK examples (NEVER produce these):\n"
            f"- \"What is a transformer?\"  - \"Why is this topic important?\"  "
            f"- \"What are the benefits of X?\"\n\n"
            f"Return ONLY the questions, one per line, no numbering, no commentary."
        )
        raw = large_model(prompt, system=system, max_tokens=600, temperature=0.5)
        return self._parse_questions(raw, n)

    @staticmethod
    def _parse_questions(raw: Optional[str], n: int) -> List[str]:
        if not raw:
            return []
        out: List[str] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip leading list markers / numbering ("1.", "-", "*", "Q:").
            line = re.sub(r"^(\d+[\.\)]\s*|[-*•]\s*|Q\s*[:\-]\s*)", "", line, flags=re.IGNORECASE).strip()
            if len(line) < 12:
                continue
            if "?" not in line:
                line = line.rstrip(".") + "?"
            out.append(line)
            if len(out) >= n:
                break
        return out

    def _heuristic_questions(self, topic: str, themes: Dict[str, Any], n: int) -> List[str]:
        """Gap-oriented fallback — still research-leaning, no LLM required."""
        topic = topic or "this area"
        gaps = [str(g) for g in (themes.get("gaps") or []) if str(g).strip()]
        taxonomy = [str(t) for t in (themes.get("taxonomy") or []) if str(t).strip()]
        themes_str = ", ".join(taxonomy[:4]) or topic

        questions: List[str] = []
        for g in gaps:
            questions.append(
                f"What methodological limitation underlies the gap \"{g}\", and how "
                f"does it constrain conclusions across {themes_str}?"
            )
        templates = [
            f"Where do existing approaches to {topic} disagree, and what experimental "
            f"confound could explain the contradiction?",
            f"Under what conditions (scale, distribution shift, failure modes) do the "
            f"reported results for {topic} fail to generalize?",
            f"Which assumptions in the {themes_str} literature remain untested, and "
            f"what falsifiable hypothesis would test them?",
            f"What trade-off (e.g. accuracy vs. efficiency vs. robustness) is most "
            f"under-examined in current {topic} research?",
            f"What open problem in {topic} would most change the field if resolved, "
            f"and why has prior work not addressed it?",
        ]
        for t in templates:
            if len(questions) >= n:
                break
            questions.append(t)
        return questions[:n]

    # ------------------------------------------------------------------
    # Answer generation
    # ------------------------------------------------------------------

    def _llm_answer(self, question: str, refs: List[Dict[str, Any]], topic: str) -> Optional[str]:
        try:
            from backend.runtime.models import large_model
        except Exception:
            return None
        if not refs:
            return None
        ref_block = "\n".join(
            f"- {r.get('title','')}: {(r.get('abstract','') or '')[:300]}" for r in refs
        )
        system = (
            "You answer research questions strictly from the provided sources. "
            "You do not invent facts. If the sources are insufficient, you say so "
            "and state what evidence would be needed."
        )
        prompt = (
            f"Research question: {question}\n\n"
            f"Answer ONLY from these sources (topic: \"{topic}\"):\n{ref_block}\n\n"
            f"Write a concise, evidence-grounded answer (3-5 sentences). Reference "
            f"the sources by title where they support a claim. If evidence is "
            f"missing or conflicting, say so explicitly. Return ONLY the answer prose."
        )
        return large_model(prompt, system=system, max_tokens=400, temperature=0.3)

    def _heuristic_answer(self, question: str, refs: List[Dict[str, Any]], topic: str) -> str:
        """Stitch the most relevant abstract sentences, with attribution."""
        if not refs:
            return (
                f"The retrieved literature does not directly resolve this question for "
                f"{topic or 'the topic'}; addressing it would require targeted evidence "
                f"beyond the current corpus."
            )
        parts: List[str] = []
        for r in refs[:2]:
            title = r.get("title", "")
            abstract = (r.get("abstract", "") or "").strip()
            sentence = re.split(r"(?<=[.!?])\s+", abstract)[0] if abstract else ""
            if sentence and title:
                parts.append(f"“{title}” notes that {sentence[0].lower()}{sentence[1:]}")
            elif title:
                parts.append(f"“{title}” is relevant evidence")
        body = " ".join(parts)
        return (
            f"{body} Taken together, these sources partially inform the question, but "
            f"a definitive answer remains open across the surveyed work."
        ).strip()

    # ------------------------------------------------------------------
    # Vector / lexical retrieval (mirrors DraftingAgent)
    # ------------------------------------------------------------------

    def _build_index(self, corpus: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not corpus:
            return None
        model = _get_embed_model()
        if model is None:
            return {"kind": "lexical", "corpus": corpus}
        try:
            docs = [f"{p.get('title', '')}. {p.get('abstract', '')}"[:512] for p in corpus]
            emb = model.encode(docs, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
            try:
                import faiss
                index = faiss.IndexFlatIP(emb.shape[1])
                index.add(emb)
                return {"kind": "faiss", "index": index, "corpus": corpus, "model": model}
            except Exception:
                return {"kind": "numpy", "emb": emb, "corpus": corpus, "model": model}
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] QA index build failed: {exc}")
            return {"kind": "lexical", "corpus": corpus}

    def _retrieve_refs(
        self, query: str, corpus: List[Dict[str, Any]], index: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not corpus or index is None:
            return []
        cap = min(_REFS_PER_QUESTION, len(corpus))
        kind = index.get("kind")

        if kind in ("faiss", "numpy"):
            try:
                model = index["model"]
                q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
                if kind == "faiss":
                    _scores, idxs = index["index"].search(q, cap)
                    order = idxs[0]
                else:
                    sims = (index["emb"] @ q[0])
                    order = sims.argsort()[::-1][:cap]
                return [corpus[i] for i in order if 0 <= i < len(corpus)]
            except Exception as exc:  # noqa: BLE001
                print(f"   [!] QA vector retrieval failed, using lexical: {exc}")

        terms = set(_tokens(query))
        scored = sorted(
            corpus,
            key=lambda p: len(terms & set(_tokens(f"{p.get('title','')} {p.get('abstract','')}"))),
            reverse=True,
        )
        return scored[:cap]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return [w for w in _TOKEN_RE.findall((text or "").lower()) if len(w) > 3]
