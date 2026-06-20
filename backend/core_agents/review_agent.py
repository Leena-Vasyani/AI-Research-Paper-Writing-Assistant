"""
Review Agent — independent multi-critic peer reviewer.

Implements the Review architecture diagram: a panel of specialized critics, each
scoring the draft (optionally against the knowledge sources / Citation Graph),
plus the plagiarism agent folded in as an originality critic. Produces per-axis
scores, flagged contradictions, unsupported-claim severities, major concerns, a
recommendation, and structured per-section critique that feeds the graph's
revision loop (review -> drafting).

Critics:
  - Novelty Evaluator            (score /10)
  - Coherence Checker            (score /10)
  - Logical Consistency          (flag contradictions)
  - Evidence Quality             (score /10)
  - Unsupported Claim Detector   (severity H/M/L)
  - Writing & Reproducibility    (score /10)
  - Originality                  (score /10, from the plagiarism agent)

Every critic has an offline heuristic fallback, so the agent always returns a
well-formed review without an LLM. The output keeps ``mean_score`` and
``has_critical_issues`` (consumed by the graph's ``_after_review`` conditional).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

# Reuse the Outline Agent's robust JSON extraction.
try:
    from backend.core_agents.outline_agent import _extract_json
except Exception:  # pragma: no cover
    def _extract_json(text):  # type: ignore
        import json
        try:
            return json.loads(text or "")
        except Exception:
            return None

_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%?\b")
_COMPARATIVE_RE = re.compile(
    r"\b(outperform\w*|state[- ]of[- ]the[- ]art|significantly|superior|best|"
    r"better than|improv\w*|achiev\w*|surpass\w*|highest|lowest|fastest)\b",
    re.IGNORECASE,
)
_CITATION_HINT_RE = re.compile(r"\[\d+\]|\(\d{4}\)|et al\.|“[^”]+”|\"[^\"]+\"")

_SCORE_AXES = ["novelty", "coherence", "evidence_quality", "writing_reproducibility", "originality"]
_CRITICAL_SCORE = 4.0


class ReviewAgent:
    def __init__(
        self,
        use_llm: bool = True,
        use_plagiarism: bool = True,
        review_threshold: float = 7.0,
        max_workers: int = 4,
    ):
        self.use_llm = use_llm
        self.use_plagiarism = use_plagiarism
        self.review_threshold = review_threshold
        self.max_workers = max_workers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(
        self,
        draft: Dict[str, Any],
        *,
        topic: str = "",
        corpus: Optional[List[Dict[str, Any]]] = None,
        citation_graph: Optional[Dict[str, Any]] = None,
        blueprint: Optional[Dict[str, Any]] = None,
        plagiarism_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        corpus = corpus or []
        citation_graph = citation_graph or {}
        blueprint = blueprint or {}
        sections: Dict[str, str] = draft.get("sections", {}) if isinstance(draft, dict) else {}
        full_text = "\n\n".join(f"{n}\n{t}" for n, t in sections.items())

        # Originality via plagiarism (folded-in critic).
        if plagiarism_report is None and self.use_plagiarism:
            plagiarism_report = self._run_plagiarism(sections, corpus, topic)
        plagiarism_report = plagiarism_report or {}

        scores: Dict[str, float] = {}
        scores["originality"] = self._originality_score(plagiarism_report)

        # Run the scoring critics (parallel when using the LLM).
        critic_specs = [
            ("novelty", self._novelty),
            ("coherence", self._coherence),
            ("evidence_quality", self._evidence_quality),
            ("writing_reproducibility", self._writing_reproducibility),
        ]
        ctx = {"topic": topic, "corpus": corpus, "blueprint": blueprint,
               "citation_graph": citation_graph, "full_text": full_text, "sections": sections}

        if self.use_llm and self._llm_available():
            with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                results = ex.map(lambda kv: (kv[0], kv[1](ctx)), critic_specs)
                for key, val in results:
                    scores[key] = val
            method = "llm"
        else:
            for key, fn in critic_specs:
                scores[key] = fn(ctx)
            method = "heuristic"

        contradictions = self._logical_consistency(ctx)
        unsupported = self._unsupported_claims(sections)

        mean_score = round(sum(scores[a] for a in _SCORE_AXES) / len(_SCORE_AXES), 2)
        has_critical = self._has_critical(scores, contradictions, unsupported, plagiarism_report)
        major_concerns = self._major_concerns(scores, contradictions, unsupported, plagiarism_report)
        critique = self._build_critique(scores, contradictions, unsupported, sections)
        recommendation = self._recommend(mean_score, has_critical)

        return {
            "scores": scores,
            "logical_consistency": {"contradictions": contradictions},
            "unsupported_claims": unsupported,
            "mean_score": mean_score,
            "has_critical_issues": has_critical,
            "major_concerns": major_concerns,
            "recommendation": recommendation,
            "critique": critique,
            "plagiarism": plagiarism_report,
            "method": method,
        }

    # ------------------------------------------------------------------
    # Plagiarism / originality
    # ------------------------------------------------------------------

    def _run_plagiarism(self, sections, corpus, topic) -> Dict[str, Any]:
        try:
            from backend.core_agents.plagiarism_agent import PlagiarismDetectionAgent
            return PlagiarismDetectionAgent().check_plagiarism(sections, corpus, topic)
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Plagiarism critic unavailable: {exc}")
            return {}

    @staticmethod
    def _originality_score(report: Dict[str, Any]) -> float:
        if not report:
            return 7.0  # neutral when unavailable
        overlap = float(report.get("overall_score", 0.0) or 0.0)
        return round(max(0.0, 1.0 - overlap) * 10.0, 1)

    # ------------------------------------------------------------------
    # Scoring critics (LLM with heuristic fallback)
    # ------------------------------------------------------------------

    def _score_via_llm(self, instruction: str, ctx: Dict[str, Any]) -> Optional[float]:
        try:
            from backend.runtime.models import large_model
        except Exception:
            return None
        prompt = (
            f"You are a strict academic peer reviewer. {instruction}\n"
            f"Paper topic: {ctx.get('topic','')}\n"
            f"Manuscript (excerpt):\n{ctx.get('full_text','')[:4000]}\n"
            "Return ONLY JSON: {\"score\": <0-10 number>, \"justification\": \"<one sentence>\"}."
        )
        data = _extract_json(large_model(prompt, max_tokens=200, temperature=0.2))
        if isinstance(data, dict) and "score" in data:
            try:
                return max(0.0, min(10.0, float(data["score"])))
            except Exception:
                return None
        return None

    def _novelty(self, ctx: Dict[str, Any]) -> float:
        if self.use_llm:
            s = self._score_via_llm(
                "Score the NOVELTY of the contribution (0-10): how original vs. prior work.", ctx)
            if s is not None:
                return s
        # Heuristic: gaps explicitly addressed + corpus breadth.
        gaps = (ctx.get("blueprint") or {}).get("gaps", [])
        text = ctx.get("full_text", "").lower()
        addressed = sum(1 for g in gaps if str(g).lower()[:20] in text)
        base = 5.5 + min(2.0, 0.5 * addressed)
        if "novel" in text or "we propose" in text or "contribution" in text:
            base += 0.5
        return round(min(8.0, base), 1)

    def _coherence(self, ctx: Dict[str, Any]) -> float:
        if self.use_llm:
            s = self._score_via_llm(
                "Score COHERENCE and logical flow across sections (0-10).", ctx)
            if s is not None:
                return s
        sections = ctx.get("sections", {})
        if not sections:
            return 3.0
        lengths = [len(t.split()) for t in sections.values() if t.strip()]
        if not lengths:
            return 3.0
        # penalize empty/very-uneven sections
        nonempty_ratio = len(lengths) / max(1, len(sections))
        base = 5.0 + 3.0 * nonempty_ratio
        return round(min(8.5, base), 1)

    def _evidence_quality(self, ctx: Dict[str, Any]) -> float:
        if self.use_llm:
            s = self._score_via_llm(
                "Score EVIDENCE QUALITY: are claims grounded in cited sources (0-10)?", ctx)
            if s is not None:
                return s
        sections = ctx.get("sections", {})
        if not sections:
            return 3.0
        cited = sum(1 for t in sections.values() if _CITATION_HINT_RE.search(t or ""))
        ratio = cited / max(1, len(sections))
        return round(min(9.0, 3.5 + 5.5 * ratio), 1)

    def _writing_reproducibility(self, ctx: Dict[str, Any]) -> float:
        if self.use_llm:
            s = self._score_via_llm(
                "Score WRITING quality and REPRODUCIBILITY (methodology detail) (0-10).", ctx)
            if s is not None:
                return s
        sections = {k.lower(): v for k, v in ctx.get("sections", {}).items()}
        score = 5.0
        if any("method" in k for k in sections):
            score += 1.5
        if any("result" in k or "experiment" in k for k in sections):
            score += 1.0
        total_words = sum(len(v.split()) for v in sections.values())
        if total_words > 1500:
            score += 0.5
        return round(min(8.5, score), 1)

    # ------------------------------------------------------------------
    # Logical consistency + unsupported claims
    # ------------------------------------------------------------------

    def _logical_consistency(self, ctx: Dict[str, Any]) -> List[str]:
        if self.use_llm:
            try:
                from backend.runtime.models import large_model
                prompt = (
                    "Identify any internal contradictions or logically inconsistent claims in "
                    f"this manuscript on '{ctx.get('topic','')}'.\n{ctx.get('full_text','')[:4000]}\n"
                    "Return ONLY JSON: {\"contradictions\": [\"<short description>\", ...]}. "
                    "Empty list if none."
                )
                data = _extract_json(large_model(prompt, max_tokens=300, temperature=0.2))
                if isinstance(data, dict) and isinstance(data.get("contradictions"), list):
                    return [str(c) for c in data["contradictions"]][:10]
            except Exception:
                pass
        return []  # heuristic detection of true contradictions is unreliable; none by default

    def _unsupported_claims(self, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        flagged: List[Dict[str, Any]] = []
        for name, text in sections.items():
            for sent in _SENT_RE.split(text or ""):
                s = sent.strip()
                if len(s) < 25:
                    continue
                if _CITATION_HINT_RE.search(s):
                    continue  # already grounded
                has_num = bool(_NUM_RE.search(s))
                has_cmp = bool(_COMPARATIVE_RE.search(s))
                if not (has_num or has_cmp):
                    continue
                severity = "H" if (has_num and has_cmp) else "M" if has_cmp else "L"
                flagged.append({"section": name, "claim": s[:200], "severity": severity})
                if len(flagged) >= 25:
                    return flagged
        return flagged

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def _has_critical(self, scores, contradictions, unsupported, plagiarism) -> bool:
        if (plagiarism or {}).get("overall_status") == "high":
            return True
        if any(c.get("severity") == "H" for c in unsupported):
            return True
        if contradictions:
            return True
        if any(v < _CRITICAL_SCORE for v in scores.values()):
            return True
        return False

    def _major_concerns(self, scores, contradictions, unsupported, plagiarism) -> List[str]:
        concerns: List[str] = []
        for axis, val in scores.items():
            if val < 6.0:
                concerns.append(f"Low {axis.replace('_', ' ')} score ({val}/10)")
        high = [c for c in unsupported if c["severity"] == "H"]
        if high:
            concerns.append(f"{len(high)} high-severity unsupported claim(s)")
        if contradictions:
            concerns.append(f"{len(contradictions)} logical inconsistency(ies)")
        if (plagiarism or {}).get("overall_status") == "high":
            concerns.append("High textual overlap with sources (originality)")
        return concerns

    def _build_critique(self, scores, contradictions, unsupported, sections) -> Dict[str, List[str]]:
        critique: Dict[str, List[str]] = {"general": []}
        if scores.get("coherence", 10) < 6.0:
            critique["general"].append("Improve transitions and logical flow across sections.")
        if scores.get("evidence_quality", 10) < 6.0:
            critique["general"].append("Ground more claims in cited sources.")
        if scores.get("novelty", 10) < 6.0:
            critique["general"].append("Sharpen the statement of novel contributions.")
        for c in contradictions:
            critique["general"].append(f"Resolve contradiction: {c}")
        for claim in unsupported:
            sec = claim["section"]
            critique.setdefault(sec, []).append(
                f"[{claim['severity']}] Add a citation for: \"{claim['claim'][:80]}...\""
            )
        return critique

    def _recommend(self, mean_score: float, has_critical: bool) -> str:
        if has_critical:
            return "reject" if mean_score < 5.5 else "revise"
        if mean_score >= 8.0:
            return "accept"
        if mean_score >= self.review_threshold - 0.5:
            return "weak_accept"
        return "revise"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _llm_available(self) -> bool:
        if not self.use_llm:
            return False
        try:
            from backend.core_agents.llm_provider import active_providers
            return bool(active_providers())
        except Exception:
            return False
