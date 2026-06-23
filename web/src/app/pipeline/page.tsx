"use client";

import { useState } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import { ManuscriptView, QAView } from "@/components/pipeline/PipelineCards";
import { api } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Pipeline run failed";
}

function scoreColor(v: number): string {
  if (v >= 8) return "text-emerald-300";
  if (v >= 6) return "text-amber-300";
  return "text-rose-300";
}

export default function PipelinePage() {
  const [topic, setTopic] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);

  const run = async () => {
    if (!topic.trim()) {
      setError("Enter a research topic first.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const res = await api.runPipeline({
        topic,
        target_venue: venue,
        output_type: outputType,
        constraints: { max_results: maxResults },
      });
      setResult(res);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const review = result?.review;
  const blueprint = result?.blueprint;
  const qa = result?.qa;
  const doc = result?.final_document;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Multi-agent runtime"
        title="Research Pipeline"
        subtitle="Search → Topic Mining → Research Q&A → Outline → Drafting → Review → Citation gate → Formatter, orchestrated end-to-end with a revision loop."
      />

      <SectionCard
        title="Run the pipeline"
        description="Provide a topic and target venue; the orchestrator coordinates every agent."
      >
        <div className="grid gap-3 md:grid-cols-2">
          <label className="md:col-span-2 text-sm text-zinc-300">
            Research topic
            <input
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. graph neural networks for smart grid load forecasting"
            />
          </label>
          <label className="text-sm text-zinc-300">
            Target venue
            <select
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
            >
              <option>IEEE</option>
              <option>ACM</option>
              <option>Springer</option>
            </select>
          </label>
          <label className="text-sm text-zinc-300">
            Output type
            <select
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={outputType}
              onChange={(e) => setOutputType(e.target.value)}
            >
              <option value="research_paper">Research paper</option>
              <option value="survey">Survey</option>
              <option value="report">Report</option>
            </select>
          </label>
          <label className="text-sm text-zinc-300">
            Max papers
            <input
              type="number"
              min={3}
              max={20}
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={maxResults}
              onChange={(e) => setMaxResults(Number(e.target.value))}
            />
          </label>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={run}
            disabled={loading}
            className="rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-50"
          >
            {loading ? "Running pipeline…" : "Run pipeline"}
          </button>
          {result?.stage_timings && (
            <span className="text-xs text-zinc-500">
              {Object.entries(result.stage_timings)
                .map(([s, t]) => `${s} ${t}s`)
                .join(" · ")}
            </span>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
      </SectionCard>

      {result && (
        <>
          {result.warnings && result.warnings.length > 0 && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              {result.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          {/* Review report — Scores / Concerns / Recommendation */}
          {review && (
            <SectionCard
              title="Review report"
              description="Independent multi-critic peer review."
              actions={
                <Badge>
                  {review.recommendation?.replace("_", " ") ?? "n/a"}
                </Badge>
              }
            >
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-zinc-500">
                    Scores
                  </div>
                  <ul className="mt-2 space-y-1 text-sm">
                    {Object.entries(review.scores ?? {}).map(([k, v]) => (
                      <li key={k} className="flex justify-between gap-3">
                        <span className="text-zinc-400">
                          {k.replace(/_/g, " ")}
                        </span>
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
                    Unsupported claims
                  </div>
                  <div className="mt-2 text-sm text-zinc-300">
                    {(review.unsupported_claims ?? []).length} flagged
                    {result.revision_count != null && (
                      <div className="mt-1 text-xs text-zinc-500">
                        revisions: {result.revision_count}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </SectionCard>
          )}

          {/* Research Q&A — research-level questions + grounded answers */}
          {qa && (qa.qa_pairs?.length ?? 0) > 0 && (
            <SectionCard
              title="Research Q&A"
              description="Research-level questions answered from the corpus — grounds the Introduction & Related Work."
              actions={<Badge>{`${qa.qa_pairs?.length ?? 0} Q&A`}</Badge>}
            >
              <QAView qa={qa} />
            </SectionCard>
          )}

          {/* Blueprint */}
          {blueprint && (
            <SectionCard
              title="Outline blueprint"
              description={`${blueprint.sections?.length ?? 0} sections · venue ${blueprint.target_venue ?? "?"}`}
            >
              <div className="space-y-2">
                {(blueprint.sections ?? []).map((s) => (
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
              </div>
              {blueprint.gaps && blueprint.gaps.length > 0 && (
                <div className="mt-3 text-xs text-zinc-400">
                  <span className="text-zinc-500">Gaps: </span>
                  {blueprint.gaps.join("; ")}
                </div>
              )}
            </SectionCard>
          )}

          {/* Final document */}
          {doc && (
            <SectionCard title="Manuscript" description={`${doc.title ?? ""}`}>
              <ManuscriptView doc={doc} />
            </SectionCard>
          )}
        </>
      )}
    </div>
  );
}
