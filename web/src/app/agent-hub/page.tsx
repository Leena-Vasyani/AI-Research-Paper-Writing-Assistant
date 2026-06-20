"use client";

import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";
import {
  BlueprintView,
  CorpusView,
  ManuscriptView,
  ReviewReport,
  ThemesView,
} from "@/components/pipeline/PipelineCards";

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Pipeline run failed";
}

export default function AgentHubPage() {
  const [topic, setTopic] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);
  const [maxRevisions, setMaxRevisions] = useState(2);
  const [notes, setNotes] = useState("");
  const [latexTemplate, setLatexTemplate] = useState("");

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
      const raw_materials: Record<string, unknown> = {};
      if (notes.trim()) raw_materials.notes = notes;
      if (latexTemplate.trim()) raw_materials.latex_template = latexTemplate;
      const res = await api.runPipeline({
        topic,
        target_venue: venue,
        output_type: outputType,
        constraints: { max_results: maxResults },
        raw_materials,
        max_revisions: maxRevisions,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const cgNodes =
    (result?.citation_graph?.["stats"] as { node_count?: number } | undefined)?.node_count ??
    (result?.citation_graph?.["nodes"] as unknown[] | undefined)?.length ??
    0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Multi-agent runtime"
        title="Agent Hub"
        subtitle="Run the entire orchestrated pipeline in one shot and inspect every agent's output — corpus, themes, blueprint, review scores, and the final manuscript."
      />

      <SectionCard
        title="Run full pipeline"
        description="The orchestrator runs Search → Topic Mining → Outline → Drafting → Review (with revision loop) → Citation gate → Formatter."
      >
        <div className="grid gap-3 md:grid-cols-2">
          <label className="md:col-span-2 text-sm text-zinc-300">
            Research topic
            <input
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. reinforcement learning for home energy management"
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
          <label className="text-sm text-zinc-300">
            Max revisions
            <input
              type="number"
              min={0}
              max={5}
              className="mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={maxRevisions}
              onChange={(e) => setMaxRevisions(Number(e.target.value))}
            />
          </label>
          <label className="md:col-span-2 text-sm text-zinc-300">
            Raw notes / experimental logs (optional)
            <textarea
              className="mt-1 h-20 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-zinc-100 outline-none focus:border-indigo-400/60"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Pasted notes, results tables, ablation logs…"
            />
          </label>
          <label className="md:col-span-2 text-sm text-zinc-300">
            Conference LaTeX template (optional — overrides section structure)
            <textarea
              className="mt-1 h-20 w-full rounded-xl border border-zinc-800 bg-zinc-950/70 px-3 py-2 font-mono text-xs text-zinc-100 outline-none focus:border-indigo-400/60"
              value={latexTemplate}
              onChange={(e) => setLatexTemplate(e.target.value)}
              placeholder="\\section{Introduction}\\section{Method}…"
            />
          </label>
        </div>
        <div className="mt-4">
          <button
            onClick={run}
            disabled={loading}
            className="rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-50"
          >
            {loading ? "Running full pipeline…" : "Run full pipeline"}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
      </SectionCard>

      {result && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Papers" value={String(result.corpus?.length ?? 0)} />
            <StatCard label="Citation graph nodes" value={String(cgNodes)} />
            <StatCard
              label="Review mean"
              value={result.review?.mean_score != null ? `${result.review.mean_score}/10` : "—"}
            />
            <StatCard label="Revisions" value={String(result.revision_count ?? 0)} />
          </div>

          {result.warnings && result.warnings.length > 0 && (
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              {result.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          <SectionCard title="Retrieved corpus">
            <CorpusView corpus={result.corpus} />
          </SectionCard>

          <SectionCard title="Themes & gaps">
            <ThemesView themes={result.themes} />
          </SectionCard>

          <SectionCard title="Outline blueprint">
            <BlueprintView blueprint={result.blueprint} />
          </SectionCard>

          <SectionCard title="Review report">
            <ReviewReport review={result.review} revisionCount={result.revision_count} />
          </SectionCard>

          <SectionCard title="Manuscript" description={result.final_document?.title}>
            <ManuscriptView doc={result.final_document} />
          </SectionCard>
        </>
      )}
    </div>
  );
}
