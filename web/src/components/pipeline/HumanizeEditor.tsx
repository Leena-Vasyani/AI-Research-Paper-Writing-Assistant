"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { wordDiffStats } from "@/lib/humanize";
import type { GrammarIssue } from "@/lib/types";

type Props = {
  name: string;
  original: string;
  value: string;
  editable: boolean;
  fraction: number;
  onChange: (name: string, text: string) => void;
};

/**
 * One section of the humanization gate: an editable textarea with a live
 * word-change progress bar (for gated body sections) plus on-demand grammar
 * assistance whose fixes the author accepts or rejects. All state lives in the
 * parent via `onChange`; this component only owns its transient grammar list.
 */
export default function HumanizeEditor({
  name,
  original,
  value,
  editable,
  fraction,
  onChange,
}: Props) {
  const [issues, setIssues] = useState<GrammarIssue[] | null>(null);
  const [checking, setChecking] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const stats = wordDiffStats(original, value, editable, fraction);
  const pct =
    stats.required > 0
      ? Math.min(100, Math.round((stats.changed / stats.required) * 100))
      : 100;

  const checkGrammar = async () => {
    setNote(null);
    abortRef.current?.abort();
    const text = value.trim();
    if (!text) {
      setIssues([]);
      return;
    }
    setChecking(true);
    try {
      const res = await api.grammarCheck({ text, max_issues: 8 });
      setIssues(res.issues ?? []);
    } catch {
      setIssues([]);
      setNote("Grammar check unavailable right now.");
    } finally {
      setChecking(false);
    }
  };

  const acceptFix = (issue: GrammarIssue) => {
    const idx = value.indexOf(issue.original_snippet);
    if (idx === -1) {
      // The surrounding text changed since the check — drop this stale card.
      setIssues((prev) => prev?.filter((i) => i !== issue) ?? null);
      setNote("Some suggestions went stale after edits — re-check grammar.");
      return;
    }
    const next =
      value.slice(0, idx) + issue.suggestion + value.slice(idx + issue.original_snippet.length);
    onChange(name, next);
    setIssues((prev) => prev?.filter((i) => i !== issue) ?? null);
  };

  const rejectFix = (issue: GrammarIssue) => {
    setIssues((prev) => prev?.filter((i) => i !== issue) ?? null);
  };

  return (
    <div className="rounded-2xl border border-zinc-800/80 bg-zinc-950/50 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-100">{name}</span>
          {editable ? (
            <span
              className={`rounded-md px-2 py-0.5 text-[11px] ${
                stats.met
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-amber-500/15 text-amber-300"
              }`}
            >
              {stats.met ? "✓ humanized" : "edit required"}
            </span>
          ) : (
            <span className="rounded-md bg-zinc-700/40 px-2 py-0.5 text-[11px] text-zinc-400">
              auto · not required
            </span>
          )}
        </div>
        <span className="text-[11px] text-zinc-500">
          {stats.originalWords}w original → {stats.editedWords}w now
        </span>
      </div>

      {editable && stats.required > 0 && (
        <div className="mb-2">
          <div className="mb-1 flex items-center justify-between text-[11px]">
            <span className={stats.met ? "text-emerald-300" : "text-amber-300"}>
              changed {stats.changed} / {stats.required} words
            </span>
            {!stats.lengthOk && (
              <span className="text-rose-300">
                too short — keep ≥ {stats.lengthFloor}w (rewrite, don&apos;t delete)
              </span>
            )}
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
            <div
              className={`h-full rounded-full transition-all ${
                stats.met ? "bg-emerald-400" : "bg-amber-400"
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      <textarea
        className="h-48 w-full resize-y rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 text-xs leading-relaxed text-zinc-100 outline-none focus:border-indigo-400/60"
        value={value}
        readOnly={!editable}
        onChange={(e) => onChange(name, e.target.value)}
        spellCheck
      />

      <div className="mt-2 flex items-center gap-2">
        <button
          onClick={checkGrammar}
          disabled={checking}
          className="rounded-lg bg-zinc-800/70 px-3 py-1 text-xs text-zinc-200 transition hover:bg-zinc-700/70 disabled:opacity-40"
        >
          {checking ? "Checking…" : "Check grammar"}
        </button>
        {issues != null && !checking && (
          <span className="text-[11px] text-zinc-500">
            {issues.length === 0 ? "no issues found" : `${issues.length} suggestion(s)`}
          </span>
        )}
        {note && <span className="text-[11px] text-amber-300">{note}</span>}
      </div>

      {issues && issues.length > 0 && (
        <ul className="mt-2 space-y-2">
          {issues.map((issue, i) => (
            <li
              key={`${issue.original_snippet}-${i}`}
              className="rounded-xl border border-zinc-800/80 bg-zinc-900/50 px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-indigo-300">
                  {issue.category || "grammar"}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => acceptFix(issue)}
                    className="rounded bg-emerald-500/15 px-2 py-0.5 text-[11px] text-emerald-300 hover:bg-emerald-500/25"
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => rejectFix(issue)}
                    className="rounded bg-zinc-700/40 px-2 py-0.5 text-[11px] text-zinc-300 hover:bg-zinc-600/40"
                  >
                    Reject
                  </button>
                </div>
              </div>
              <div className="mt-1 text-xs">
                <span className="text-rose-300/90 line-through">{issue.original_snippet}</span>
                <span className="mx-1 text-zinc-500">→</span>
                <span className="text-emerald-300">{issue.suggestion}</span>
              </div>
              {issue.explanation && (
                <p className="mt-1 text-[11px] text-zinc-400">{issue.explanation}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
