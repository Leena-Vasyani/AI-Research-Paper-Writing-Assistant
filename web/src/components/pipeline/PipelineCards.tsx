"use client";

import { useState } from "react";
import Badge from "@/components/Badge";
import type {
  Paper,
  PipelineBlueprint,
  PipelineFinalDocument,
  PipelineReview,
  QAResult,
} from "@/lib/types";

export function scoreColor(v: number): string {
  if (v >= 8) return "text-emerald-300";
  if (v >= 6) return "text-amber-300";
  return "text-rose-300";
}

// ── Corpus ────────────────────────────────────────────────────────────────

export function CorpusView({ corpus }: { corpus?: Paper[] }) {
  if (!corpus || corpus.length === 0)
    return <p className="text-sm text-zinc-500">No papers retrieved.</p>;
  return (
    <ul className="space-y-2">
      {corpus.map((p, i) => (
        <li
          key={p.entry_id ?? p.url ?? i}
          className="rounded-xl border border-zinc-800/80 bg-zinc-950/50 px-3 py-2"
        >
          <div className="flex items-start justify-between gap-3">
            <span className="text-sm text-zinc-100">{p.title}</span>
            <span className="shrink-0 text-xs text-zinc-500">
              {p.source} · {p.citations ?? 0} cites
            </span>
          </div>
          {p.authors_str && (
            <div className="mt-0.5 text-xs text-zinc-500">{p.authors_str}</div>
          )}
        </li>
      ))}
    </ul>
  );
}

// ── Themes ──────────────────────────────────────────────────────────────────

type Cluster = { theme?: string; keywords?: string[]; size?: number };

export function ThemesView({ themes }: { themes?: Record<string, unknown> }) {
  const clusters = (themes?.clusters as Cluster[] | undefined) ?? [];
  const gaps = (themes?.gaps as string[] | undefined) ?? [];
  if (clusters.length === 0)
    return <p className="text-sm text-zinc-500">No themes mined yet.</p>;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {clusters.map((c, i) => (
          <span
            key={i}
            className="rounded-lg border border-zinc-800/80 bg-zinc-950/50 px-2.5 py-1 text-xs text-zinc-200"
          >
            {c.theme} {typeof c.size === "number" && (
              <span className="text-zinc-500">· {c.size}</span>
            )}
          </span>
        ))}
      </div>
      {gaps.length > 0 && (
        <div className="text-xs text-zinc-400">
          <span className="text-zinc-500">Gaps: </span>
          {gaps.join("; ")}
        </div>
      )}
    </div>
  );
}

// ── Research Q&A ────────────────────────────────────────────────────────────

export function QAView({ qa }: { qa?: QAResult }) {
  const pairs = qa?.qa_pairs ?? [];
  if (pairs.length === 0)
    return (
      <p className="text-sm text-zinc-500">
        No research questions generated yet.
      </p>
    );
  return (
    <div className="space-y-2">
      {qa?.method && (
        <div className="text-xs text-zinc-500">generator: {qa.method}</div>
      )}
      {pairs.map((p, i) => (
        <details
          key={i}
          className="rounded-xl border border-zinc-800/80 bg-zinc-950/50 px-3 py-2"
          open={i === 0}
        >
          <summary className="cursor-pointer text-sm font-medium text-zinc-100">
            <span className="mr-1.5 text-indigo-300">Q{i + 1}.</span>
            {p.question}
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-300">
            {p.answer || "(no grounded answer)"}
          </p>
          {p.sources && p.sources.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {p.sources.map((s, j) => (
                <span
                  key={j}
                  className="rounded-md border border-zinc-800/80 bg-zinc-900/60 px-2 py-0.5 text-[11px] text-zinc-400"
                  title={s}
                >
                  {s.length > 48 ? `${s.slice(0, 48)}…` : s}
                </span>
              ))}
            </div>
          )}
        </details>
      ))}
    </div>
  );
}

// ── Blueprint ────────────────────────────────────────────────────────────────

export function BlueprintView({ blueprint }: { blueprint?: PipelineBlueprint }) {
  if (!blueprint || !blueprint.sections)
    return <p className="text-sm text-zinc-500">No blueprint generated.</p>;
  return (
    <div className="space-y-2">
      {blueprint.sections.map((s) => (
        <div
          key={s.name}
          className="rounded-xl border border-zinc-800/80 bg-zinc-950/50 px-3 py-2"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium text-zinc-100">{s.name}</span>
            <span className="text-xs text-zinc-500">
              {s.role} · ~{s.target_words ?? 0}w
            </span>
          </div>
          {s.subsections && s.subsections.length > 0 && (
            <div className="mt-1 text-xs text-zinc-400">
              {s.subsections.map((sub) => sub.name).join(" · ")}
            </div>
          )}
        </div>
      ))}
      {blueprint.gaps && blueprint.gaps.length > 0 && (
        <div className="text-xs text-zinc-400">
          <span className="text-zinc-500">Gaps: </span>
          {blueprint.gaps.join("; ")}
        </div>
      )}
    </div>
  );
}

// ── Review report ────────────────────────────────────────────────────────────

export function ReviewReport({
  review,
  revisionCount,
}: {
  review?: PipelineReview;
  revisionCount?: number;
}) {
  if (!review) return <p className="text-sm text-zinc-500">No review yet.</p>;
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div>
        <div className="text-xs uppercase tracking-wide text-zinc-500">Scores</div>
        <ul className="mt-2 space-y-1 text-sm">
          {Object.entries(review.scores ?? {}).map(([k, v]) => (
            <li key={k} className="flex justify-between gap-3">
              <span className="text-zinc-400">{k.replace(/_/g, " ")}</span>
              <span className={scoreColor(v)}>{v}/10</span>
            </li>
          ))}
          <li className="mt-1 flex justify-between gap-3 border-t border-zinc-800 pt-1 font-medium">
            <span>mean</span>
            <span className={scoreColor(review.mean_score ?? 0)}>
              {review.mean_score}/10
            </span>
          </li>
        </ul>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wide text-zinc-500">
          Major concerns
        </div>
        <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-zinc-300">
          {(review.major_concerns ?? []).length === 0 ? (
            <li className="list-none text-zinc-500">None flagged</li>
          ) : (
            review.major_concerns!.map((c, i) => <li key={i}>{c}</li>)
          )}
        </ul>
      </div>
      <div>
        <div className="text-xs uppercase tracking-wide text-zinc-500">
          Verdict
        </div>
        <div className="mt-2 space-y-1 text-sm text-zinc-300">
          <Badge tone={review.has_critical_issues ? "warning" : "success"}>
            {review.recommendation?.replace("_", " ") ?? "n/a"}
          </Badge>
          <div className="text-xs text-zinc-500">
            {(review.unsupported_claims ?? []).length} unsupported claim(s)
          </div>
          {revisionCount != null && (
            <div className="text-xs text-zinc-500">revisions: {revisionCount}</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Manuscript (final document) ───────────────────────────────────────────────

export function ManuscriptView({ doc }: { doc?: PipelineFinalDocument }) {
  const [tab, setTab] = useState<"markdown" | "latex">("markdown");
  const [copied, setCopied] = useState(false);
  if (!doc) return <p className="text-sm text-zinc-500">No manuscript yet.</p>;

  const content = doc.formats?.[tab] ?? "";
  const ext = tab === "latex" ? "tex" : "md";
  const filename = `${(doc.title || "manuscript").replace(/[^a-z0-9]+/gi, "_").slice(0, 60) || "manuscript"}.${ext}`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };
  const download = () => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        {(["markdown", "latex"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1 text-xs transition ${
              tab === t
                ? "bg-indigo-500/25 text-indigo-100"
                : "bg-zinc-800/60 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {t}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={copy}
            disabled={!content}
            className="rounded-lg bg-zinc-800/60 px-3 py-1 text-xs text-zinc-200 transition hover:bg-zinc-700/70 disabled:opacity-40"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
          <button
            onClick={download}
            disabled={!content}
            className="rounded-lg bg-zinc-800/60 px-3 py-1 text-xs text-zinc-200 transition hover:bg-zinc-700/70 disabled:opacity-40"
          >
            Download .{ext}
          </button>
          <Badge tone={doc.export_ready ? "success" : "warning"}>
            {doc.export_ready ? "export ready" : "grounding incomplete"}
          </Badge>
        </div>
      </div>
      <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap rounded-xl border border-zinc-800 bg-zinc-950/70 p-4 text-xs leading-relaxed text-zinc-200">
        {content || "(no content)"}
      </pre>
      {doc.figures && doc.figures.length > 0 && (
        <div className="mt-3 text-xs text-zinc-400">
          <span className="text-zinc-500">Figures: </span>
          {doc.figures.map((f) => `${f.type} (${f.section})`).join(" · ")}
        </div>
      )}
      {doc.references && doc.references.length > 0 && (
        <div className="mt-2 text-xs text-zinc-500">
          {doc.references.length} reference(s)
        </div>
      )}
    </div>
  );
}
