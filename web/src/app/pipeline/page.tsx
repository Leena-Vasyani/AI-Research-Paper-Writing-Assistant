"use client";

import { useState } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import { ManuscriptView, QAView } from "@/components/pipeline/PipelineCards";
import HumanizePanel from "@/components/pipeline/HumanizePanel";
import FieldSelector from "@/components/FieldSelector";
import { api } from "@/lib/api";
import { DEFAULT_FIELD_ID, getField } from "@/lib/fields";
import type { PipelineResult } from "@/lib/types";

type Phase = "input" | "humanize" | "finalizing" | "done";

// Sequentially fold single stages over an accumulating state (mirrors the graph
// order, minus the revision loop — human edits must flow forward, not re-draft).
async function runStages(
  stages: string[],
  initial: Record<string, unknown>,
): Promise<PipelineResult> {
  let s = initial;
  for (const stage of stages) {
    s = (await api.runStage({ stage, state: s })) as unknown as Record<string, unknown>;
  }
  return s as unknown as PipelineResult;
}

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
  const [field, setField] = useState(DEFAULT_FIELD_ID);
  const [subfield, setSubfield] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);
  const [humanizeOn, setHumanizeOn] = useState(true);
  const [humanizeFraction, setHumanizeFraction] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("input");
  const [draftState, setDraftState] = useState<PipelineResult | null>(null);
  const [result, setResult] = useState<PipelineResult | null>(null);

  // Field change resets the subfield and applies the discipline's default venue.
  const handleFieldChange = (f: string, s: string) => {
    setSubfield(s);
    if (f !== field) {
      setField(f);
      setVenue(getField(f).defaults.venue);
    }
  };

  const run = async () => {
    if (!topic.trim()) {
      setError("Enter a research topic first.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    setDraftState(null);
    setPhase("input");

    // Toggle OFF: the original one-click, fully-automated run (unchanged).
    if (!humanizeOn) {
      try {
        const res = await api.runPipeline({
          topic,
          target_venue: venue,
          output_type: outputType,
          constraints: { max_results: maxResults, field, subfield },
        });
        setResult(res);
        setPhase("done");
      } catch (e: unknown) {
        setError(getErrorMessage(e));
        setPhase("input");
      } finally {
        setLoading(false);
      }
      return;
    }

    // Toggle ON: generate up to the draft, then stop for the humanization gate.
    setPhase("input");
    try {
      const seed: Record<string, unknown> = {
        topic,
        target_venue: venue,
        output_type: outputType,
        constraints: { max_results: maxResults, humanize_fraction: humanizeFraction, field, subfield },
      };
      const drafted = await runStages(
        ["search", "topic_mining", "qa", "outline", "drafting"],
        seed,
      );
      setDraftState(drafted);
      setPhase("humanize");
    } catch (e: unknown) {
      setError(getErrorMessage(e));
      setPhase("input");
    } finally {
      setLoading(false);
    }
  };

  // After the author humanizes: splice edited sections into the draft and run the
  // remaining stages (review → citation → formatter) on the human-edited content.
  const finalize = async (edited: Record<string, string>) => {
    if (!draftState) return;
    setError(null);
    setPhase("finalizing");
    try {
      const base: Record<string, unknown> = {
        ...(draftState as unknown as Record<string, unknown>),
        draft: { ...draftState.draft, sections: edited },
      };
      const finalized = await runStages(["review", "citation", "formatter"], base);
      setResult(finalized);
      setPhase("done");
    } catch (e: unknown) {
      setError(getErrorMessage(e));
      setPhase("humanize");
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
              placeholder={getField(field).placeholder}
            />
          </label>
          <FieldSelector field={field} subfield={subfield} onChange={handleFieldChange} />
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
          <label className="md:col-span-2 flex items-center gap-2 text-sm text-zinc-300">
            <input
              type="checkbox"
              checked={humanizeOn}
              onChange={(e) => setHumanizeOn(e.target.checked)}
              className="h-4 w-4 accent-indigo-400"
            />
            Require manual humanization — edit each body section before review to cut
            plagiarism
          </label>
          {humanizeOn && (
            <label className="md:col-span-2 text-sm text-zinc-300">
              Humanization strictness ·{" "}
              <span className="text-indigo-200">
                rewrite ≥ {Math.round(humanizeFraction * 100)}% of words per body section
              </span>
              <input
                type="range"
                min={10}
                max={60}
                step={5}
                value={Math.round(humanizeFraction * 100)}
                onChange={(e) => setHumanizeFraction(Number(e.target.value) / 100)}
                className="mt-2 w-full accent-indigo-400"
              />
            </label>
          )}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={run}
            disabled={loading || phase === "finalizing"}
            className="rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-50"
          >
            {loading
              ? humanizeOn
                ? "Generating draft…"
                : "Running pipeline…"
              : humanizeOn
                ? "Generate draft"
                : "Run pipeline"}
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

      {phase === "humanize" && draftState?.draft && (
        <SectionCard
          title="Humanize the draft"
          description="Rewrite each body section in your own words. Review, citation and formatting run on your edited text."
        >
          <HumanizePanel
            draft={draftState.draft}
            state={draftState}
            fraction={humanizeFraction}
            busy={phase !== "humanize"}
            confirmLabel="Confirm & run review + formatting"
            onConfirm={finalize}
          />
        </SectionCard>
      )}

      {phase === "finalizing" && (
        <div className="rounded-2xl border border-indigo-400/25 bg-indigo-500/10 px-4 py-3 text-sm text-indigo-100">
          Running review → citation → formatting on your humanized draft…
        </div>
      )}

      {phase === "done" && result && (
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
