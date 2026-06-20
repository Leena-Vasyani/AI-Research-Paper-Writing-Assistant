"""
Track A — deterministic, offline keyword expansion.

Combines a small in-code domain thesaurus (ML/CS/energy acronyms ⇄ expansions)
with WordNet synonyms + hypernyms. Fully guarded: if NLTK / WordNet data is
unavailable it degrades to the domain thesaurus only (and returns ``{}`` when
nothing matches), so callers never need to handle errors.
"""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger("thesaurus")

# Bidirectional acronym ⇄ expansion pairs for common technical terms.
_DOMAIN_THESAURUS: Dict[str, List[str]] = {
    "cnn": ["convolutional neural network"],
    "rnn": ["recurrent neural network"],
    "lstm": ["long short-term memory"],
    "gnn": ["graph neural network"],
    "llm": ["large language model"],
    "nlp": ["natural language processing"],
    "rl": ["reinforcement learning"],
    "drl": ["deep reinforcement learning"],
    "gan": ["generative adversarial network"],
    "vae": ["variational autoencoder"],
    "ev": ["electric vehicle"],
    "v2g": ["vehicle to grid"],
    "hems": ["home energy management system"],
    "mpc": ["model predictive control"],
    "soc": ["state of charge"],
    "iot": ["internet of things"],
    "cv": ["computer vision"],
    "asr": ["automatic speech recognition"],
}

_WORDNET = None  # None=unchecked, False=unavailable, else the wordnet module


def _ensure_wordnet():
    global _WORDNET
    if _WORDNET is not None:
        return _WORDNET
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        try:
            wn.ensure_loaded()
        except LookupError:
            nltk.download("wordnet", quiet=True)
            nltk.download("omw-1.4", quiet=True)
            wn.ensure_loaded()
        _WORDNET = wn
    except Exception as exc:  # noqa: BLE001 - optional dependency / data
        logger.info("WordNet unavailable (%s); using domain thesaurus only", exc)
        _WORDNET = False
    return _WORDNET


def _wordnet_terms(term: str, max_terms: int = 4) -> List[str]:
    wn = _ensure_wordnet()
    if not wn:
        return []
    out: List[str] = []
    seen = set()
    try:
        for syn in wn.synsets(term.replace(" ", "_"))[:3]:
            for lemma in syn.lemmas():
                w = lemma.name().replace("_", " ").lower()
                if w != term and w not in seen:
                    seen.add(w)
                    out.append(w)
            for hyp in syn.hypernyms()[:2]:
                for lemma in hyp.lemmas()[:2]:
                    w = lemma.name().replace("_", " ").lower()
                    if w != term and w not in seen:
                        seen.add(w)
                        out.append(w)
            if len(out) >= max_terms:
                break
    except Exception:  # noqa: BLE001
        pass
    return out[:max_terms]


def expand_terms(keywords: List[str], max_per_term: int = 4) -> Dict[str, List[str]]:
    """Return ``{keyword: [synonyms/hypernyms/expansions]}`` for each keyword."""
    result: Dict[str, List[str]] = {}
    for kw in keywords or []:
        kw_l = (kw or "").strip().lower()
        if not kw_l:
            continue
        terms: List[str] = []

        # Domain thesaurus (both directions: acronym→expansion and reverse).
        if kw_l in _DOMAIN_THESAURUS:
            terms.extend(_DOMAIN_THESAURUS[kw_l])
        for acr, vals in _DOMAIN_THESAURUS.items():
            if kw_l in vals:
                terms.append(acr)

        # WordNet only for single tokens (phrases produce noisy synsets).
        if " " not in kw_l:
            terms.extend(_wordnet_terms(kw_l, max_per_term))

        # Dedupe, drop self.
        seen = set()
        uniq: List[str] = []
        for t in terms:
            if t and t != kw_l and t not in seen:
                seen.add(t)
                uniq.append(t)
        result[kw] = uniq[:max_per_term]
    return result
