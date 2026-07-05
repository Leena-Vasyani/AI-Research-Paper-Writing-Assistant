/**
 * Human-in-the-loop humanization metric — frontend mirror of
 * `backend/runtime/humanize.py`. Keep the two byte-for-byte equivalent (same
 * tokenizer, constants, and formulas): this drives the live per-section progress
 * bar, while the Python copy is the authoritative gate at /api/humanize/validate.
 *
 * Metric (per editable section):
 *   changed  = origWords - wordLcs(origWords, editedWords)
 *   required = origWords < 25 ? 0 : ceil(fraction * origWords)
 *   met      = changed >= required AND edited keeps >= 70% of original length
 */

import type { HumanizeSectionMeta } from "./types";

// Unicode-agnostic on purpose: mirror the Python WORD_RE exactly.
const WORD_RE = /[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*/g;

export const DEFAULT_FRACTION = 0.4;
export const MIN_WORDS_TO_REQUIRE = 25;
export const LENGTH_FLOOR_RATIO = 0.7;

// Substantive body-prose roles that are gated (mirror EDITABLE_ROLES in Python).
const EDITABLE_ROLES = new Set(["body", "macro_lit_review", "micro_lit_review"]);

export function tokenize(text: string): string[] {
  if (!text) return [];
  const matches = text.toLowerCase().match(WORD_RE);
  return matches ? Array.from(matches) : [];
}

/** Longest common subsequence length of two token lists (rolling row). */
export function wordLcsLen(a: string[], b: string[]): number {
  if (a.length === 0 || b.length === 0) return 0;
  if (b.length > a.length) {
    const t = a;
    a = b;
    b = t;
  }
  let prev = new Array<number>(b.length + 1).fill(0);
  for (let i = 0; i < a.length; i += 1) {
    const curr = new Array<number>(b.length + 1).fill(0);
    const tokenA = a[i];
    for (let j = 1; j <= b.length; j += 1) {
      if (tokenA === b[j - 1]) {
        curr[j] = prev[j - 1] + 1;
      } else {
        curr[j] = curr[j - 1] >= prev[j] ? curr[j - 1] : prev[j];
      }
    }
    prev = curr;
  }
  return prev[b.length];
}

export function changedWords(original: string, edited: string): number {
  const o = tokenize(original);
  const e = tokenize(edited);
  if (o.length === 0) return e.length;
  return o.length - wordLcsLen(o, e);
}

export function requiredChanges(original: string, fraction = DEFAULT_FRACTION): number {
  const n = tokenize(original).length;
  if (n < MIN_WORDS_TO_REQUIRE) return 0;
  return Math.ceil(fraction * n);
}

export function isEditable(role?: string): boolean {
  return EDITABLE_ROLES.has(role || "");
}

export type WordDiffStats = {
  editable: boolean;
  originalWords: number;
  editedWords: number;
  changed: number;
  required: number;
  lengthFloor: number;
  lengthOk: boolean;
  met: boolean;
};

/**
 * Live per-section status. `editable` should come from the draft's humanize meta
 * (role-based); pass it through so non-body sections are never gated.
 */
export function wordDiffStats(
  original: string,
  edited: string,
  editable: boolean,
  fraction = DEFAULT_FRACTION,
): WordDiffStats {
  const o = tokenize(original);
  const e = tokenize(edited);
  const originalWords = o.length;
  const editedWords = e.length;
  const changed = originalWords === 0 ? editedWords : originalWords - wordLcsLen(o, e);
  const required = originalWords < MIN_WORDS_TO_REQUIRE ? 0 : Math.ceil(fraction * originalWords);
  const lengthFloor = Math.floor(LENGTH_FLOOR_RATIO * originalWords);
  const lengthOk = !editable || originalWords === 0 || editedWords >= lengthFloor;
  const met = !editable || (changed >= required && lengthOk);
  return { editable, originalWords, editedWords, changed, required, lengthFloor, lengthOk, met };
}

/**
 * Whether every editable section has met its quota. `metaSections` is
 * `draft.humanize.sections`; `edited` is the current per-section text. Sections
 * without meta fall back to non-editable (never blocks).
 */
export function allSectionsMet(
  original: Record<string, string>,
  edited: Record<string, string>,
  metaSections: Record<string, HumanizeSectionMeta> | undefined,
  fraction = DEFAULT_FRACTION,
): boolean {
  return Object.keys(original).every((name) => {
    const editable = metaSections?.[name]?.editable ?? false;
    if (!editable) return true;
    return wordDiffStats(original[name] ?? "", edited[name] ?? "", true, fraction).met;
  });
}
