"use client";

import { useEffect, useMemo, useState } from "react";
import HumanizeEditor from "@/components/pipeline/HumanizeEditor";
import { api } from "@/lib/api";
import { DEFAULT_FRACTION, wordDiffStats } from "@/lib/humanize";
import type { PipelineDraft, PipelineResult } from "@/lib/types";

type Props = {
  draft: PipelineDraft;
  /** Full pipeline state — enables the authoritative server-side quota re-check. */
  state?: PipelineResult;
  /** Overrides draft.humanize.fraction for live stats + validation. */
  fraction?: number;
  onConfirm: (editedSections: Record<string, string>) => void | Promise<void>;
  confirmLabel?: string;
  busy?: boolean;
};

/**
 * The reusable human-in-the-loop humanization gate. Drops into any page that has
 * produced `draft.sections`: renders a per-section editor, tracks the change
 * quota, and only enables "confirm" once every body section is sufficiently
 * rewritten. On confirm it (optionally) re-validates on the server, then hands
 * the edited sections back to the caller to splice into `state.draft.sections`.
 */
export default function HumanizePanel({
  draft,
  state,
  fraction: fractionProp,
  onConfirm,
  confirmLabel = "Confirm humanization & continue",
  busy = false,
}: Props) {
  const original = useMemo(
    () => draft.original_sections ?? draft.sections ?? {},
    [draft.original_sections, draft.sections],
  );
  const meta = draft.humanize;
  const fraction = fractionProp ?? meta?.fraction ?? DEFAULT_FRACTION;

  const [edited, setEdited] = useState<Record<string, string>>(() => ({
    ...(draft.sections ?? original),
  }));
  const [validating, setValidating] = useState(false);
  const [failed, setFailed] = useState<string[] | null>(null);

  // Re-seed only when a fresh draft is produced (new pristine baseline), NOT on
  // every keystroke or on confirm (which keeps the same original_sections ref).
  useEffect(() => {
    setEdited({ ...(draft.sections ?? {}) });
    setFailed(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.original_sections]);

  const names = useMemo(() => {
    const ordered = draft.ordering?.filter((n) => n in original) ?? [];
    const rest = Object.keys(original).filter((n) => !ordered.includes(n));
    return [...ordered, ...rest];
  }, [draft.ordering, original]);

  const setSection = (name: string, text: string) =>
    setEdited((prev) => ({ ...prev, [name]: text }));

  const editableNames = names.filter((n) => meta?.sections?.[n]?.editable);
  const metCount = editableNames.filter(
    (n) => wordDiffStats(original[n] ?? "", edited[n] ?? "", true, fraction).met,
  ).length;
  const allMet = metCount === editableNames.length;
  const hasBaseline = !!draft.original_sections;

  const confirm = async () => {
    setFailed(null);
    if (state) {
      setValidating(true);
      try {
        const payload = {
          ...(state as unknown as Record<string, unknown>),
          draft: { ...draft, sections: edited },
        };
        const res = await api.validateHumanization({
          state: payload,
          humanize_fraction: fraction,
        });
        if (!res.passed) {
          setFailed(res.failures.map((f) => f.name));
          return;
        }
      } catch {
        // Server validation unavailable — fall back to the client-side gate,
        // which already required allMet before this button was enabled.
      } finally {
        setValidating(false);
      }
    }
    await onConfirm(edited);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-indigo-400/25 bg-indigo-500/10 px-4 py-3">
        <div className="text-sm text-indigo-100">
          <span className="font-semibold">Humanize the draft.</span> Rewrite at least{" "}
          {Math.round(fraction * 100)}% of the words in each body section — this lowers
          plagiarism and makes the writing yours.
        </div>
        <span
          className={`shrink-0 rounded-md px-2 py-0.5 text-xs ${
            allMet ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"
          }`}
        >
          {metCount}/{editableNames.length} body sections done
        </span>
      </div>

      {!hasBaseline && (
        <p className="text-xs text-amber-300">
          No original baseline on this draft — re-run drafting to enable the change quota.
        </p>
      )}

      {names.map((name) => (
        <HumanizeEditor
          key={name}
          name={name}
          original={original[name] ?? ""}
          value={edited[name] ?? ""}
          editable={!!meta?.sections?.[name]?.editable}
          fraction={fraction}
          onChange={setSection}
        />
      ))}

      {failed && failed.length > 0 && (
        <p className="text-xs text-rose-300">
          These sections still need more edits: {failed.join(", ")}.
        </p>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={confirm}
          disabled={!allMet || busy || validating}
          className="rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-40"
          title={allMet ? "" : "Meet the change quota in every body section first"}
        >
          {validating ? "Validating…" : busy ? "Working…" : confirmLabel}
        </button>
        {!allMet && (
          <span className="text-xs text-zinc-500">
            Finish humanizing every body section to continue.
          </span>
        )}
      </div>
    </div>
  );
}
