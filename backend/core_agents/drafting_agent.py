"""
Drafting Agent — turns the Outline Blueprint into a submission-ready manuscript.

Implements the Drafting architecture diagram:
    Receive Blueprint
      -> Parallel Section Dispatch
      -> Subsection Writer (~1000 words/section)
      -> Vector Retrieval (FAISS, capped at 25% refs per section)
      -> Data Extraction (tables / ablations / figures from raw materials)
      -> Write Body First, then Title -> Abstract -> Conclusion
      -> per-section Verify Structure & Citations -> Delta-Feedback refine
      -> LaTeX Renderer

Generation uses the large model tier (Ollama -> Groq -> Gemini). It degrades
gracefully to deterministic, reference-grounded synthesis when no LLM is
available, so the pipeline always yields a complete, valid draft offline.

The old fine-tuned FLAN-T5 drafter is retained only as an optional fallback
(``use_finetuned_fallback=True``).

Returns (consumed by Review/Citation nodes — ``sections`` stays a flat
``{name: text}`` dict for back-compat):

    {
      "sections": {section_name: text, ...},
      "latex": "...",
      "section_meta": {name: {"words", "refs_used": [...], "verified", "issues"}},
      "references_used": [paper, ...],
      "ordering": [...],
      "method": "llm" | "deterministic",
    }
"""

from __future__ import annotations

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend.core_agents.search_agent import _get_embed_model
except Exception:  # pragma: no cover
    _get_embed_model = lambda: None  # type: ignore[assignment]

try:
    from backend.core_agents.outline_agent import _extract_json
except Exception:  # pragma: no cover
    def _extract_json(text):  # type: ignore
        import json
        try:
            return json.loads(text or "")
        except Exception:
            return None


_REF_CAP_FRACTION = float(os.getenv("DRAFT_REF_CAP_FRACTION", "0.25"))
_WORDS_PER_SECTION = int(os.getenv("DRAFT_WORDS_PER_SECTION", "1000"))


def _env_flag(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in ("0", "false", "no", "")


# --- Originality / anti-overlap controls (all env-overridable) -------------
_DRAFT_TEMPERATURE = float(os.getenv("DRAFT_TEMPERATURE", "0.7"))
_DISTILL_REFS = _env_flag("DRAFT_DISTILL_REFS", "1")
_ORIGINALITY_PASS = _env_flag("DRAFT_ORIGINALITY_PASS", "1")
_ORIGINALITY_MAX_PASSES = int(os.getenv("DRAFT_ORIGINALITY_MAX_PASSES", "2"))
# Cap rewrites per section per pass so the originality stage stays bounded in cost
# (the most-overlapping sentences are rewritten first).
_ORIGINALITY_MAX_REWRITES = int(os.getenv("DRAFT_ORIGINALITY_MAX_REWRITES", "15"))
_TARGET_OVERLAP = float(os.getenv("DRAFT_TARGET_OVERLAP", "0.28"))

# System message that enforces original academic synthesis (anti-copying). It is
# sent on every section-generation call so the model treats sources as grounding,
# not text to reuse.
_ORIGINALITY_SYSTEM = (
    "You are an expert academic author writing an original manuscript. Write "
    "entirely in your own words: synthesize and contrast ideas across multiple "
    "sources rather than restating any single one. Never copy or lightly reword "
    "phrases or sentence structures from the provided source notes — the notes "
    "are factual grounding only, not text to reuse. Integrate at least two "
    "sources for each major claim and attribute ideas in your own phrasing "
    "(e.g. 'X et al. report ...'). Vary sentence length and structure and avoid "
    "formulaic or repetitive transitions. Maintain a formal, precise academic "
    "register."
)


class DraftingAgent:
    def __init__(
        self,
        use_llm: bool = True,
        words_per_section: int = _WORDS_PER_SECTION,
        ref_cap_fraction: float = _REF_CAP_FRACTION,
        max_refine_loops: int = 1,
        max_workers: int = 4,
        use_finetuned_fallback: bool = False,
    ):
        self.use_llm = use_llm
        self.words_per_section = words_per_section
        self.ref_cap_fraction = ref_cap_fraction
        self.max_refine_loops = max_refine_loops
        self.max_workers = max_workers
        self.use_finetuned_fallback = use_finetuned_fallback
        # Single, lazily-loaded plagiarism agent reused by the originality pass
        # (the SentenceTransformer is expensive to load, so load it at most once).
        self._plagiarism = None
        self._plag_lock = threading.Lock()
        # Cache of (source_sentences, embeddings) keyed by id(corpus) so the
        # corpus is encoded once, not once per section (sections run in parallel).
        self._src_cache: Dict[int, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draft(
        self,
        blueprint: Dict[str, Any],
        corpus: List[Dict[str, Any]],
        *,
        topic: Optional[str] = None,
        raw_materials: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        review_feedback: Optional[Dict[str, Any]] = None,
        qa: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        corpus = corpus or []
        raw_materials = raw_materials or {}
        qa = qa or {}
        topic = topic or blueprint.get("topic", "")
        venue = blueprint.get("target_venue", "IEEE")
        sections_spec = blueprint.get("sections", [])

        # Build the vector index once (FAISS if available, else lexical).
        index = self._build_index(corpus)

        # Partition sections: body (written first, in parallel) vs deferred
        # (Abstract/Conclusion depend on the body) vs auto (References).
        body_specs, deferred_specs = [], []
        for spec in sections_spec:
            name = spec.get("name", "")
            role = spec.get("role", "body")
            if name.lower() == "references":
                continue  # generated by Citation/Formatter
            if role in ("front_matter", "back_matter") and name.lower() in ("abstract", "conclusion"):
                deferred_specs.append(spec)
            else:
                body_specs.append(spec)

        section_text: Dict[str, str] = {}
        section_meta: Dict[str, Any] = {}
        refs_used_all: Dict[str, Dict[str, Any]] = {}

        # Shared, plan-level context so parallel section writers stay coherent
        # (each knows the title, every other section's goal, and a glossary)
        # without needing the other sections' actual text.
        glossary = self._build_glossary(blueprint, corpus)
        shared_context = self._build_shared_context(blueprint, topic, glossary)

        # Pre-render the research-level Q&A grounding once; injected only into the
        # Introduction / lit-review sections (see _qualifies_for_qa).
        qa_block = self._build_qa_block(qa)

        # --- Parallel Section Dispatch for body sections ---
        def _work(spec: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any], List[Dict[str, Any]]]:
            name = spec.get("name", "Section")
            refs = self._retrieve_refs(spec, corpus, index)
            data = self._extract_data(spec, raw_materials)
            text = self._generate_section(
                spec, refs, data, topic, context=shared_context, feedback=review_feedback,
                qa_block=qa_block if self._qualifies_for_qa(spec) else "",
            )
            text, meta = self._verify_and_refine(spec, text, refs)
            # Targeted originality pass: rewrite only the sentences that overlap
            # the source corpus, until the section is under the overlap target.
            text = self._originality_pass(name, text, corpus, topic)
            meta["words"] = _word_count(text)
            return name, text, meta, refs

        if body_specs:
            workers = max(1, min(self.max_workers, len(body_specs)))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for name, text, meta, refs in ex.map(_work, body_specs):
                    section_text[name] = text
                    section_meta[name] = meta
                    for r in refs:
                        refs_used_all[r.get("title", "")] = r

        # --- Body context for the deferred sections ---
        body_context = "\n\n".join(
            f"{n}:\n{t}" for n, t in section_text.items()
        )[:6000]

        # --- Conclusion, then Abstract (both summarize the body) ---
        for spec in sorted(deferred_specs, key=lambda s: 0 if s["name"].lower() == "conclusion" else 1):
            name = spec.get("name", "Section")
            text = self._generate_section(spec, [], "", topic, context=body_context)
            section_text[name] = text
            section_meta[name] = {"words": _word_count(text), "refs_used": [], "verified": True, "issues": []}
            body_context = (body_context + "\n\n" + name + ":\n" + text)[:7000]

        # --- Title ---
        title = self._write_title(topic, blueprint, body_context)

        # Order sections as in the blueprint (minus References).
        ordering = [s["name"] for s in sections_spec if s["name"].lower() != "references"]
        ordered_sections = {n: section_text.get(n, "") for n in ordering}

        latex = self._to_latex(title, ordered_sections, sections_spec, venue,
                               list(refs_used_all.values()))

        method = "llm" if (self.use_llm and self._llm_available()) else "deterministic"
        return {
            "title": title,
            "sections": ordered_sections,
            "latex": latex,
            "section_meta": section_meta,
            "references_used": list(refs_used_all.values()),
            "ordering": ordering,
            "method": method,
        }

    # ------------------------------------------------------------------
    # Vector retrieval (FAISS, capped per section)
    # ------------------------------------------------------------------

    def _build_index(self, corpus: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Embed the corpus and build a FAISS index (falls back to lexical)."""
        if not corpus:
            return None
        model = _get_embed_model()
        if model is None:
            return {"kind": "lexical", "corpus": corpus}
        try:
            import numpy as np
            docs = [f"{p.get('title', '')}. {p.get('abstract', '')}"[:512] for p in corpus]
            emb = model.encode(docs, convert_to_numpy=True, normalize_embeddings=True).astype("float32")
            try:
                import faiss
                index = faiss.IndexFlatIP(emb.shape[1])
                index.add(emb)
                return {"kind": "faiss", "index": index, "corpus": corpus, "model": model}
            except Exception:
                # numpy cosine fallback (vectors normalized => dot product)
                return {"kind": "numpy", "emb": emb, "corpus": corpus, "model": model}
        except Exception as exc:  # noqa: BLE001
            print(f"   [!] Draft index build failed: {exc}")
            return {"kind": "lexical", "corpus": corpus}

    def _ref_cap(self, corpus_len: int) -> int:
        return max(1, round(self.ref_cap_fraction * corpus_len)) if corpus_len else 0

    def _retrieve_refs(
        self, spec: Dict[str, Any], corpus: List[Dict[str, Any]], index: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not corpus or index is None:
            return []
        cap = self._ref_cap(len(corpus))
        query = self._section_query(spec)
        kind = index.get("kind")

        if kind in ("faiss", "numpy"):
            try:
                import numpy as np
                model = index["model"]
                q = model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
                if kind == "faiss":
                    _scores, idxs = index["index"].search(q, min(cap, len(corpus)))
                    order = idxs[0]
                else:
                    sims = (index["emb"] @ q[0])
                    order = sims.argsort()[::-1][:cap]
                return [corpus[i] for i in order if 0 <= i < len(corpus)]
            except Exception as exc:  # noqa: BLE001
                print(f"   [!] Vector retrieval failed, using lexical: {exc}")

        # Lexical fallback: keyword overlap with the section query.
        terms = set(_tokens(query))
        scored = sorted(
            corpus,
            key=lambda p: len(terms & set(_tokens(f"{p.get('title','')} {p.get('abstract','')}"))),
            reverse=True,
        )
        return scored[:cap]

    @staticmethod
    def _section_query(spec: Dict[str, Any]) -> str:
        cues = " ".join(
            c for sub in spec.get("subsections", []) for c in sub.get("cues", [])
        )
        return f"{spec.get('name', '')} {spec.get('goal', '')} {cues}".strip()

    # ------------------------------------------------------------------
    # Data extraction (tables / ablations / figures)
    # ------------------------------------------------------------------

    def _extract_data(self, spec: Dict[str, Any], raw_materials: Dict[str, Any]) -> str:
        """Summarize raw experimental materials relevant to body sections."""
        name = spec.get("name", "").lower()
        if not raw_materials or not any(k in name for k in ("method", "result", "experiment", "evaluation", "analysis")):
            return ""
        parts: List[str] = []
        for key in ("experimental_logs", "logs", "tables", "results", "metrics", "ablation", "figures"):
            val = raw_materials.get(key)
            if val:
                parts.append(f"{key}: {str(val)[:800]}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Section generation
    # ------------------------------------------------------------------

    def _llm_available(self) -> bool:
        if not self.use_llm:
            return False
        try:
            from backend.core_agents.llm_provider import active_providers
            return bool(active_providers())
        except Exception:
            return False

    def _generate_section(
        self, spec: Dict[str, Any], refs: List[Dict[str, Any]], data: str,
        topic: str, context: str = "", feedback: Optional[Dict[str, Any]] = None,
        qa_block: str = "",
    ) -> str:
        target = spec.get("target_words") or self.words_per_section
        if self.use_llm:
            text = self._llm_section(spec, refs, data, topic, context, target, feedback, qa_block)
            if text:
                return text
            if self.use_finetuned_fallback:
                ft = self._finetuned_section(spec, topic, context)
                if ft:
                    return ft
        return self._deterministic_section(spec, refs, data, topic, context)

    def _model_for_section(self, spec: Dict[str, Any]):
        """Route a section to the appropriate model tier (multiple SLMs per
        section): short summarizing sections → small model; substantive
        body/lit-review sections → large model. Env override per type."""
        from backend.runtime.models import small_model, large_model
        role = spec.get("role", "body")
        name = (spec.get("name", "") or "").strip().lower()
        if role in ("front_matter", "back_matter") or name in ("abstract", "conclusion", "title"):
            return small_model
        # optional per-type override hook (e.g. DRAFT_METHODOLOGY_MODEL) is read
        # inside llm_provider via env; here we just pick the capable tier.
        return large_model

    def _build_glossary(self, blueprint: Dict[str, Any], corpus: List[Dict[str, Any]]) -> List[str]:
        """One small-model call to fix shared terminology across all sections."""
        if not self.use_llm:
            return []
        try:
            from backend.runtime.models import small_model
        except Exception:
            return []
        themes = ", ".join((blueprint.get("themes") or [])[:8])
        titles = "; ".join(p.get("title", "") for p in corpus[:8])
        raw = small_model(
            f"List 6-12 key technical terms/acronyms (comma-separated, no prose) to use "
            f"consistently across a paper on '{blueprint.get('topic', '')}'. "
            f"Themes: {themes}. Sources: {titles}",
            max_tokens=120,
            temperature=0.2,
        )
        if not raw:
            return []
        return [t.strip() for t in re.split(r"[,\n]", raw) if t.strip()][:12]

    def _build_shared_context(self, blueprint: Dict[str, Any], topic: str, glossary: List[str]) -> str:
        """Plan-level context injected into every section prompt."""
        title = blueprint.get("title_hint") or topic
        plan = "; ".join(
            f"{s.get('name')}: {s.get('goal', '')}"
            for s in blueprint.get("sections", [])
            if (s.get("name", "") or "").lower() != "references"
        )
        lines = [f"Paper title: {title}", f"Section plan — {plan}"]
        if glossary:
            lines.append("Use this terminology consistently: " + ", ".join(glossary))
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Q&A grounding (Introduction / lit-review only)
    # ------------------------------------------------------------------

    @staticmethod
    def _qualifies_for_qa(spec: Dict[str, Any]) -> bool:
        """Inject Q&A grounding only into Introduction and lit-review sections.

        The Outline agent tags Introduction as ``macro_lit_review`` and Related
        Work / Background as ``micro_lit_review``; both count as lit-review.
        """
        name = (spec.get("name", "") or "").strip().lower()
        role = spec.get("role", "body")
        return (
            "introduction" in name
            or "related work" in name
            or role in ("macro_lit_review", "micro_lit_review")
        )

    def _build_qa_block(self, qa: Optional[Dict[str, Any]]) -> str:
        """Render the QAAgent output into a compact prompt block (capped)."""
        pairs = (qa or {}).get("qa_pairs") or []
        if not pairs:
            return ""
        lines = [
            "Key research questions this work addresses, with evidence from the "
            "literature (weave these into the narrative; do not list them verbatim):"
        ]
        for p in pairs:
            q = (p.get("question", "") or "").strip()
            a = (p.get("answer", "") or "").strip()
            if not q:
                continue
            srcs = ", ".join(s for s in (p.get("sources") or []) if s)[:200]
            lines.append(f"- Q: {q}")
            if a:
                lines.append(f"  A: {a}" + (f" (sources: {srcs})" if srcs else ""))
        block = "\n".join(lines)
        return block[:1500]

    # ------------------------------------------------------------------
    # Source distillation (paraphrased key-points instead of raw abstracts)
    # ------------------------------------------------------------------

    def _distill_ref(self, paper: Dict[str, Any]) -> str:
        """Paraphrased factual key-points for a source paper.

        Feeding the model distilled, reworded findings (instead of the raw
        abstract) is the single biggest lever against textual overlap: the model
        never sees the source's original phrasing. Cached on the paper dict so
        each source is distilled at most once across all sections.
        """
        cached = paper.get("_key_points")
        if cached:
            return cached
        abstract = (paper.get("abstract") or "").strip()
        title = (paper.get("title") or "").strip()
        if not abstract:
            paper["_key_points"] = title
            return title
        if not (_DISTILL_REFS and self.use_llm):
            kp = abstract[:240]
            paper["_key_points"] = kp
            return kp
        kp = ""
        try:
            from backend.runtime.models import small_model
            raw = small_model(
                "Summarize this research abstract as 1-2 concise factual bullet "
                "points (main finding + contribution). Paraphrase fully in your own "
                "words; do NOT copy phrases from the abstract. Return only the "
                f"bullets.\nTitle: {title}\nAbstract: {abstract[:1200]}",
                max_tokens=120,
                temperature=0.5,
            )
            kp = (raw or "").strip()
        except Exception:  # noqa: BLE001
            kp = ""
        if not kp:
            kp = abstract[:240]  # graceful fallback keeps the pipeline grounded
        kp = kp[:400]
        paper["_key_points"] = kp
        return kp

    def _llm_section(
        self, spec, refs, data, topic, context, target, feedback, qa_block="",
    ) -> Optional[str]:
        model_fn = self._model_for_section(spec)
        if model_fn is None:
            return None
        name = spec.get("name", "Section")
        cues = "; ".join(
            c for sub in spec.get("subsections", []) for c in sub.get("cues", [])
        ) or spec.get("goal", "")
        ref_block = "\n".join(
            f"- {r.get('title','')} — key points: {self._distill_ref(r)}" for r in refs
        ) or "(no specific sources retrieved)"
        fb = ""
        if feedback and feedback.get("major_concerns"):
            fb = "\nAddress these review concerns: " + "; ".join(map(str, feedback["major_concerns"]))
        ctx = f"\nManuscript plan & context:\n{context[:2000]}" if context else ""
        qa = f"\n{qa_block}\n" if qa_block else ""
        prompt = (
            f"You are writing ONE section of a single coherent academic paper on \"{topic}\".\n"
            f"{ctx}\n"
            f"Write ONLY the '{name}' section (~{target} words).\n"
            f"Goal: {spec.get('goal','')}\nWriting cues: {cues}\n"
            f"Cover ONLY this section's scope — do NOT write content owned by other "
            f"sections (see the section plan above). Synthesize the evidence below in "
            f"your OWN words; do NOT copy or closely paraphrase any source's wording. "
            f"Integrate multiple sources and attribute ideas by author/title where relevant.\n"
            f"Source notes (paraphrased grounding — reuse the ideas, not the wording):\n{ref_block}\n"
            f"{qa}"
            f"{('Experimental data:\\n' + data) if data else ''}{fb}\n"
            f"Return ONLY the section prose (no markdown headings)."
        )
        max_tokens = min(2048, int(target * 1.6) + 200)
        # Summarizing sections (abstract/conclusion/title) stay low-temperature for
        # faithful condensation; substantive body sections use a higher temperature
        # so phrasing diverges from the sources.
        role = spec.get("role", "body")
        is_summary = role in ("front_matter", "back_matter") or name.strip().lower() in (
            "abstract", "conclusion", "title",
        )
        temperature = 0.3 if is_summary else _DRAFT_TEMPERATURE
        return model_fn(
            prompt, system=_ORIGINALITY_SYSTEM, max_tokens=max_tokens, temperature=temperature
        )

    # ------------------------------------------------------------------
    # Targeted originality pass (sentence-level overlap reduction)
    # ------------------------------------------------------------------

    def _get_plagiarism(self):
        """Lazily construct one shared PlagiarismDetectionAgent (thread-safe)."""
        if self._plagiarism is not None:
            return self._plagiarism or None  # ``False`` sentinel => unavailable
        with self._plag_lock:
            if self._plagiarism is None:
                try:
                    from backend.core_agents.plagiarism_agent import PlagiarismDetectionAgent
                    self._plagiarism = PlagiarismDetectionAgent()
                except Exception as exc:  # noqa: BLE001
                    print(f"   [!] Originality pass disabled (plagiarism agent unavailable): {exc}")
                    self._plagiarism = False  # tried and failed; don't retry
        return self._plagiarism or None

    def _originality_pass(self, section_name: str, text: str, corpus: List[Dict[str, Any]], topic: str) -> str:
        """Rewrite only the sentences that overlap the source corpus.

        Bounded and guaranteed to terminate (see the per-step guards below): a
        fixed pass cap, a per-sentence acceptance test, a ``done`` set so no
        sentence is retried, and early-success / no-progress breaks. Worst case
        it returns the best text seen so far — a section can never get stuck.
        """
        if not (_ORIGINALITY_PASS and self.use_llm and _ORIGINALITY_MAX_PASSES > 0):
            return text
        if not text or not text.strip() or not corpus:
            return text
        agent = self._get_plagiarism()
        if agent is None:
            return text
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
        except Exception:  # noqa: BLE001
            return text

        # Flatten + embed all source sentences ONCE per corpus (cached/reused
        # across the parallel section writers).
        model = agent.model
        key = id(corpus)
        cached = self._src_cache.get(key)
        if cached is None:
            with self._plag_lock:
                cached = self._src_cache.get(key)
                if cached is None:
                    source_content = agent._extract_source_content(corpus)
                    sents = [s for ss in source_content.values() for s in ss]
                    if not sents:
                        self._src_cache[key] = (None, None)
                        return text
                    try:
                        emb = model.encode(sents, convert_to_numpy=True)
                    except Exception:  # noqa: BLE001
                        return text
                    cached = (sents, emb)
                    self._src_cache[key] = cached
        source_sentences, src_emb = cached
        if not source_sentences:
            return text

        def _max_sim(sentence: str) -> Tuple[float, str]:
            try:
                emb = model.encode([sentence], convert_to_numpy=True)
                sims = cosine_similarity(emb, src_emb)[0]
                j = int(np.argmax(sims))
                return float(sims[j]), source_sentences[j]
            except Exception:  # noqa: BLE001
                return 0.0, ""

        try:
            from backend.runtime.models import large_model
        except Exception:  # noqa: BLE001
            return text

        done: set = set()        # sentences we will not retry
        prev_overall: Optional[float] = None

        for _ in range(_ORIGINALITY_MAX_PASSES):
            sentences = agent._split_into_sentences(text)
            if not sentences:
                break
            sims = [_max_sim(s) for s in sentences]
            overall = sum(sc for sc, _ in sims) / len(sims)
            if overall < _TARGET_OVERLAP:
                break  # early-success: section is already under target
            if prev_overall is not None and (prev_overall - overall) < 0.005:
                break  # no-progress: last pass barely moved the needle
            prev_overall = overall

            # Fixed, finite flagged list for THIS pass (no mid-pass re-queue),
            # capped to the most-overlapping sentences to bound cost.
            flagged = [
                (s, sc, m) for s, (sc, m) in zip(sentences, sims)
                if sc >= _TARGET_OVERLAP and s not in done
            ]
            if not flagged:
                break
            flagged.sort(key=lambda x: x[1], reverse=True)
            flagged = flagged[:_ORIGINALITY_MAX_REWRITES]

            # ONE LLM call rewrites the whole batch — keeps the originality stage
            # to ~O(passes) calls per section rather than O(sentences).
            rewrites = self._rewrite_batch(large_model, [f[0] for f in flagged], topic, section_name)
            changed_any = False
            for (original, score, _match), rewritten in zip(flagged, rewrites):
                done.add(original)  # never retry, regardless of outcome
                if not rewritten or rewritten.strip() == original.strip():
                    continue
                new_score, _ = _max_sim(rewritten)
                if new_score + 1e-6 < score:  # accept only a measurable improvement
                    text = text.replace(original, rewritten, 1)
                    changed_any = True
            if not changed_any:
                break  # nothing improved this pass; further passes won't help

        return text

    def _rewrite_batch(self, large_model, sentences: List[str],
                       topic: str, section_name: str) -> List[Optional[str]]:
        """Rewrite a batch of overlapping sentences in a single LLM call.

        Returns a list aligned to ``sentences`` (``None`` where the model gave no
        usable rewrite). Using one call per batch keeps the originality pass cheap.
        """
        if not sentences:
            return []
        numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))
        prompt = (
            f"The numbered sentences below are from the '{section_name}' section of an "
            f"academic paper on \"{topic}\" and overlap their sources too closely. "
            f"Rewrite EACH so it shares no wording with the original while preserving the "
            f"exact technical meaning and a formal academic tone. Keep each to one "
            f"sentence of similar length. Do NOT invent author names, years, or citations "
            f"(citations are added separately). Return ONLY a JSON object keyed by the "
            f"same numbers, e.g. {{\"1\": \"<rewrite>\", \"2\": \"<rewrite>\"}}.\n"
            f"{numbered}"
        )
        try:
            raw = large_model(
                prompt, system=_ORIGINALITY_SYSTEM,
                max_tokens=min(2048, 80 * len(sentences) + 200),
                temperature=_DRAFT_TEMPERATURE,
            )
        except Exception:  # noqa: BLE001
            return [None] * len(sentences)
        data = _extract_json(raw)
        out: List[Optional[str]] = []
        for i in range(len(sentences)):
            val: Optional[str] = None
            if isinstance(data, dict):
                v = data.get(str(i + 1))
                if isinstance(v, str) and v.strip():
                    # Strip quotes/preamble and trailing period (the original
                    # sentence's terminator stays in the text → avoids "..").
                    val = v.strip().strip('"').strip().rstrip(" .")
            out.append(val)
        return out

    def _finetuned_section(self, spec, topic, context) -> Optional[str]:
        """Optional FLAN-T5 fallback for the classic sections."""
        try:
            from backend.fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig
            agent = get_drafting_agent(DraftingConfig())
            out = agent.generate_complete_draft(topic, {"executive_summary": context}, [])
            key = spec.get("name", "").lower().replace(" ", "_")
            return out.get(key) or out.get("introduction")
        except Exception:
            return None

    def _deterministic_section(self, spec, refs, data, topic, context) -> str:
        """Reference-grounded synthesis used when no LLM is available."""
        name = spec.get("name", "Section")
        role = spec.get("role", "body")
        paras: List[str] = []

        if role == "front_matter" and name.lower() == "abstract":
            paras.append(
                f"This paper investigates {topic}. We review the relevant literature, "
                f"describe our approach, and report findings, situating the contribution "
                f"within current research and outlining directions for future work."
            )
            return " ".join(paras)

        if name.lower() == "conclusion":
            paras.append(
                f"In this work we examined {topic}. The preceding sections synthesized "
                f"prior work, detailed the methodology, and discussed the results. "
                f"Future work should address the open challenges identified above."
            )
            return " ".join(paras)

        subs = spec.get("subsections", []) or [{"name": name, "cues": []}]
        for sub in subs:
            sub_name = sub.get("name", name)
            cue_text = "; ".join(sub.get("cues", [])) or spec.get("goal", "")
            line = f"This subsection on {sub_name} addresses {cue_text.lower()}."
            cited = [r.get("title", "") for r in refs[:2] if r.get("title")]
            if cited:
                line += " Prior work such as " + "; ".join(f"“{t}”" for t in cited) + \
                        " informs this discussion."
            paras.append(line)
        if data:
            paras.append(f"Experimental materials considered: {data[:400]}.")
        return " ".join(paras)

    def _write_title(self, topic: str, blueprint: Dict[str, Any], context: str) -> str:
        if self.use_llm:
            try:
                from backend.runtime.models import small_model
                t = small_model(
                    f"Propose a concise academic paper title for work on \"{topic}\". "
                    f"Return ONLY the title text.", max_tokens=40, temperature=0.5,
                )
                if t:
                    return t.strip().strip('"')
            except Exception:
                pass
        return blueprint.get("title_hint") or topic.strip().title()

    # ------------------------------------------------------------------
    # Verify structure & citations -> delta-feedback refine
    # ------------------------------------------------------------------

    def _verify_and_refine(
        self, spec: Dict[str, Any], text: str, refs: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        for _ in range(self.max_refine_loops + 1):
            ok, issues = self._verify_section(spec, text, refs)
            if ok or not self.use_llm:
                break
            refined = self._refine_section(spec, text, issues, refs)
            if not refined or refined == text:
                break
            text = refined
        ok, issues = self._verify_section(spec, text, refs)
        return text, {
            "words": _word_count(text),
            "refs_used": [r.get("title", "") for r in refs],
            "verified": ok,
            "issues": issues,
        }

    def _verify_section(
        self, spec: Dict[str, Any], text: str, refs: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        issues: List[str] = []
        words = _word_count(text)
        target = spec.get("target_words") or self.words_per_section
        if words < max(40, target * 0.25):
            issues.append(f"too short ({words} words, target ~{target})")
        # body sections with available refs should reference at least one
        if refs and not any((r.get("title", "")[:30].lower() in text.lower()) for r in refs):
            # not a hard failure for deterministic prose, but flag for LLM refine
            if spec.get("role") in ("body", "micro_lit_review", "macro_lit_review"):
                issues.append("no source referenced")
        return (len(issues) == 0), issues

    def _refine_section(
        self, spec: Dict[str, Any], text: str, issues: List[str], refs: List[Dict[str, Any]]
    ) -> Optional[str]:
        try:
            from backend.runtime.models import large_model
        except Exception:
            return None
        ref_block = "; ".join(r.get("title", "") for r in refs[:5])
        prompt = (
            f"Revise the following '{spec.get('name','')}' section to fix these issues: "
            f"{'; '.join(issues)}.\nWhere relevant, cite: {ref_block}.\n"
            f"Keep the academic tone. Return ONLY the revised prose.\n\n{text}"
        )
        return large_model(prompt, max_tokens=1800, temperature=0.4)

    # ------------------------------------------------------------------
    # LaTeX rendering
    # ------------------------------------------------------------------

    def _to_latex(
        self, title: str, sections: Dict[str, str], specs: List[Dict[str, Any]],
        venue: str, refs: List[Dict[str, Any]],
    ) -> str:
        documentclass = "IEEEtran" if "ieee" in (venue or "").lower() else "article"
        spec_by_name = {s.get("name", ""): s for s in specs}

        lines = [
            f"\\documentclass[conference]{{{documentclass}}}",
            "\\usepackage{graphicx}\n\\usepackage{cite}",
            "\\begin{document}",
            f"\\title{{{_tex_escape(title)}}}",
            "\\maketitle",
        ]
        for name, text in sections.items():
            role = spec_by_name.get(name, {}).get("role", "body")
            if role == "front_matter" and name.lower() == "abstract":
                lines.append(f"\\begin{{abstract}}\n{_tex_escape(text)}\n\\end{{abstract}}")
            else:
                lines.append(f"\\section{{{_tex_escape(name)}}}\n{_tex_escape(text)}")
        if refs:
            lines.append("\\begin{thebibliography}{99}")
            for i, r in enumerate(refs, 1):
                authors = r.get("authors_str") or ", ".join(r.get("authors", []) or []) or "Unknown"
                lines.append(
                    f"\\bibitem{{ref{i}}} {_tex_escape(authors)}, ``{_tex_escape(r.get('title',''))},'' "
                    f"{_tex_escape(str(r.get('published','')))}."
                )
            lines.append("\\end{thebibliography}")
        lines.append("\\end{document}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return [w for w in _TOKEN_RE.findall((text or "").lower()) if len(w) > 3]


def _word_count(text: str) -> int:
    return len((text or "").split())


def _tex_escape(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = text
    for ch, rep in replacements.items():
        out = out.replace(ch, rep)
    return out
