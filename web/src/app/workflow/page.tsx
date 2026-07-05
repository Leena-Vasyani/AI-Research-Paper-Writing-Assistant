"use client";

import { useState, type ReactNode } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";
import {
  BlueprintView,
  CorpusView,
  DraftPreview,
  ManuscriptView,
  QAView,
  ReviewReport,
  ThemesView,
} from "@/components/pipeline/PipelineCards";
import HumanizePanel from "@/components/pipeline/HumanizePanel";

type StepId =
  | "search"
  | "topic_mining"
  | "qa"
  | "outline"
  | "drafting"
  | "review"
  | "finalize";

const STEPS: { id: StepId; title: string; description: string }[] = [
  { id: "search", title: "1 · Search", description: "Discover, rank & dedupe literature; build the citation graph." },
  { id: "topic_mining", title: "2 · Topic Mining", description: "Cluster the corpus into themes and surface coverage gaps." },
  { id: "qa", title: "3 · Research Q&A", description: "Pose research-level questions and answer them from the corpus — grounds the Introduction & Related Work." },
  { id: "outline", title: "4 · Outline", description: "Generate the JSON blueprint that drives drafting." },
  { id: "drafting", title: "5 · Drafting", description: "Write sections grounded in retrieved sources; render LaTeX." },
  { id: "review", title: "6 · Review", description: "Independent multi-critic peer review with scores." },
  { id: "finalize", title: "7 · Citation & Format", description: "Grounding gate, then assemble the exportable manuscript." },
];

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Stage failed";
}

export default function WorkflowPage() {
  const [topic, setTopic] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);
  const [humanizeFraction, setHumanizeFraction] = useState(0.4);

  const [state, setState] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState<StepId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openStep, setOpenStep] = useState<StepId>("search");
  // The mandatory humanization gate: review can't run until the author has
  // rewritten each body section of the generated draft to the change quota.
  const [draftHumanized, setDraftHumanized] = useState(false);

  const done: Record<StepId, boolean> = {
    search: !!state?.corpus,
    topic_mining: !!state?.themes && Object.keys(state.themes).length > 0,
    qa: !!state?.qa && Object.keys(state.qa).length > 0,
    outline: !!state?.blueprint,
    drafting: !!state?.draft?.sections,
    review: !!state?.review,
    finalize: !!state?.final_document,
  };

  async function callStage(stage: string, baseState: Record<string, unknown>) {
    return api.runStage({ stage, state: baseState });
  }

  const runStep = async (step: StepId) => {
    setError(null);
    setLoading(step);
    // Any (re)run at or before drafting invalidates a prior humanization pass.
    if (step !== "review" && step !== "finalize") setDraftHumanized(false);
    try {
      if (step === "search") {
        if (!topic.trim()) {
          setError("Enter a research topic first.");
          return;
        }
        const res = await callStage("search", {
          topic,
          target_venue: venue,
          output_type: outputType,
          constraints: { max_results: maxResults },
        });
        setState(res);
        setOpenStep("topic_mining");
        return;
      }

      if (!state) {
        setError("Run the Search step first.");
        return;
      }
      const base = state as unknown as Record<string, unknown>;

      if (step === "finalize") {
        // citation grounding gate, then formatter
        const cited = await callStage("citation", base);
        const final = await callStage(
          "formatter",
          cited as unknown as Record<string, unknown>,
        );
        setState(final);
        return;
      }

      if (step === "drafting") {
        // Pass the strictness slider through so the drafting node stamps the
        // per-section change quota; stay on this step to run the gate.
        const draftBase = {
          ...base,
          constraints: {
            ...((base.constraints as Record<string, unknown>) ?? {}),
            humanize_fraction: humanizeFraction,
          },
        };
        const res = await callStage("drafting", draftBase);
        setState(res);
        setOpenStep("drafting");
        return;
      }

      const res = await callStage(step, base);
      setState(res);
      const order: StepId[] = ["search", "topic_mining", "qa", "outline", "drafting", "review", "finalize"];
      const next = order[order.indexOf(step) + 1];
      if (next) setOpenStep(next);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const renderStepBody = (step: StepId): ReactNode => {
    switch (step) {
      case "search":
        return (
          <div className="space-y-3">
            {state?.warnings && state.warnings.length > 0 && (
              <div className="text-xs text-amber-300">{state.warnings.join(" · ")}</div>
            )}
            <CorpusView corpus={state?.corpus} />
          </div>
        );
      case "topic_mining":
        return <ThemesView themes={state?.themes} />;
      case "qa":
        return <QAView qa={state?.qa} />;
      case "outline":
        return <BlueprintView blueprint={state?.blueprint} />;
      case "drafting":
        if (!state?.draft?.sections) return <DraftPreview draft={state?.draft} />;
        if (!draftHumanized)
          return (
            <HumanizePanel
              draft={state.draft}
              state={state}
              fraction={humanizeFraction}
              confirmLabel="Confirm humanization — unlock Review"
              onConfirm={(edited) => {
                setState((prev) =>
                  prev ? { ...prev, draft: { ...prev.draft, sections: edited } } : prev,
                );
                setDraftHumanized(true);
                setOpenStep("review");
              }}
            />
          );
        return <DraftPreview draft={state.draft} />;
      case "review":
        return <ReviewReport review={state?.review} revisionCount={state?.revision_count} />;
      case "finalize":
        return <ManuscriptView doc={state?.final_document} />;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Multi-agent runtime"
        title="Workflow"
        subtitle="Step through the orchestrated pipeline — Search → Topic Mining → Research Q&A → Outline → Drafting → Review → Citation & Format — reviewing each agent's output before advancing."
      />

      <section className="rounded-[2rem] bg-zinc-900/45 p-6 ring-1 ring-zinc-800/60 backdrop-blur-xl">
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
          <label className="md:col-span-2 text-sm text-zinc-300">
            Humanization strictness ·{" "}
            <span className="text-indigo-200">
              rewrite ≥ {Math.round(humanizeFraction * 100)}% of words per body section
            </span>
            <input
              type="range"
              min={20}
              max={60}
              step={5}
              value={Math.round(humanizeFraction * 100)}
              onChange={(e) => setHumanizeFraction(Number(e.target.value) / 100)}
              className="mt-2 w-full accent-indigo-400"
            />
          </label>
        </div>
        {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
        {state?.stage_timings && (
          <p className="mt-3 text-xs text-zinc-500">
            {Object.entries(state.stage_timings).map(([s, t]) => `${s} ${t}s`).join(" · ")}
          </p>
        )}
      </section>

      <div className="space-y-3">
        {STEPS.map((s) => {
          const isOpen = openStep === s.id;
          const canRun =
            s.id === "search" ||
            (s.id === "topic_mining" && done.search) ||
            (s.id === "qa" && done.topic_mining) ||
            (s.id === "outline" && done.qa) ||
            (s.id === "drafting" && done.outline) ||
            (s.id === "review" && done.drafting && draftHumanized) ||
            (s.id === "finalize" && done.review);
          return (
            <section
              key={s.id}
              className="overflow-hidden rounded-[2rem] bg-zinc-900/45 ring-1 ring-zinc-800/60 backdrop-blur-xl"
            >
              <button
                onClick={() => setOpenStep(isOpen ? ("" as StepId) : s.id)}
                className="flex w-full items-center justify-between gap-3 px-6 py-4 text-left"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold text-zinc-100">{s.title}</h2>
                    {done[s.id] && <Badge tone="success">done</Badge>}
                  </div>
                  <p className="mt-0.5 text-xs text-zinc-400">{s.description}</p>
                </div>
                <span className="text-zinc-500">{isOpen ? "▲" : "▼"}</span>
              </button>
              {isOpen && (
                <div className="border-t border-zinc-800/70 px-6 py-4">
                  <button
                    onClick={() => runStep(s.id)}
                    disabled={!canRun || loading !== null}
                    className="mb-4 rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-40"
                  >
                    {loading === s.id ? "Running…" : done[s.id] ? "Re-run step" : "Run step"}
                  </button>
                  {renderStepBody(s.id)}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
