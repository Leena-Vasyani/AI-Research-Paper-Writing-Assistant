"use client";

import { useMemo, useState, type ReactNode } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import { api } from "@/lib/api";
import type { PipelineResult } from "@/lib/types";
import {
  BlueprintView,
  CorpusView,
  ManuscriptView,
  ReviewReport,
  ThemesView,
} from "@/components/pipeline/PipelineCards";

type Stage =
  | "search"
  | "topic_mining"
  | "outline"
  | "drafting"
  | "review"
  | "citation"
  | "formatter";

// Each agent runs independently. `requires` lists the state keys it needs to
// produce meaningful output; `outputs` are the keys merged back (so concurrent
// runs of different agents don't clobber each other).
const AGENTS: {
  id: Stage;
  title: string;
  description: string;
  requires: (keyof PipelineResult)[];
  outputs: (keyof PipelineResult)[];
}[] = [
  { id: "search", title: "Search", description: "Discover, rank & dedupe literature; build the citation graph.", requires: [], outputs: ["corpus", "citation_graph"] },
  { id: "topic_mining", title: "Topic Mining", description: "Cluster the corpus into themes and gaps.", requires: ["corpus"], outputs: ["themes"] },
  { id: "outline", title: "Outline", description: "Generate the JSON blueprint.", requires: [], outputs: ["blueprint"] },
  { id: "drafting", title: "Drafting", description: "Write sections (FAISS-grounded) + render LaTeX.", requires: ["blueprint"], outputs: ["draft", "revision_count"] },
  { id: "review", title: "Review", description: "Multi-critic peer review with scores.", requires: ["draft"], outputs: ["review"] },
  { id: "citation", title: "Citation gate", description: "Audit factual claims for provenance.", requires: ["draft", "corpus"], outputs: ["draft"] },
  { id: "formatter", title: "Formatter", description: "Assemble the exportable manuscript.", requires: ["draft"], outputs: ["final_document"] },
];

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "Agent run failed";
}

export default function AgentHubPage() {
  const [topic, setTopic] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);

  const [state, setState] = useState<PipelineResult>({});
  const [loading, setLoading] = useState<Record<Stage, boolean>>({} as Record<Stage, boolean>);
  const [errors, setErrors] = useState<Record<Stage, string>>({} as Record<Stage, string>);
  const [stateText, setStateText] = useState("");
  const [stateErr, setStateErr] = useState<string | null>(null);

  const hasKey = (k: keyof PipelineResult): boolean => {
    const v = state[k];
    if (v == null) return false;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === "object") return Object.keys(v).length > 0;
    return true;
  };

  const runAgent = async (agent: (typeof AGENTS)[number]) => {
    setErrors((e) => ({ ...e, [agent.id]: "" }));
    setLoading((l) => ({ ...l, [agent.id]: true }));
    try {
      const base: Record<string, unknown> = {
        ...(state as Record<string, unknown>),
        topic,
        target_venue: venue,
        output_type: outputType,
        constraints: { max_results: maxResults },
      };
      const res = await api.runStage({ stage: agent.id, state: base });
      // Merge only this agent's output keys (+ warnings) so concurrent runs
      // of different agents don't overwrite each other.
      setState((prev) => {
        const merged: PipelineResult = { ...prev };
        for (const key of agent.outputs) {
          // @ts-expect-error index assignment across union keys
          merged[key] = res[key];
        }
        if (res.warnings && res.warnings.length) {
          merged.warnings = [...(prev.warnings ?? []), ...res.warnings];
        }
        return merged;
      });
    } catch (e: unknown) {
      setErrors((er) => ({ ...er, [agent.id]: getErrorMessage(e) }));
    } finally {
      setLoading((l) => ({ ...l, [agent.id]: false }));
    }
  };

  const applyStateText = () => {
    setStateErr(null);
    try {
      const parsed = JSON.parse(stateText || "{}");
      setState(parsed);
    } catch {
      setStateErr("Invalid JSON");
    }
  };

  const renderOutput = (id: Stage): ReactNode => {
    switch (id) {
      case "search":
        return <CorpusView corpus={state.corpus} />;
      case "topic_mining":
        return <ThemesView themes={state.themes} />;
      case "outline":
        return <BlueprintView blueprint={state.blueprint} />;
      case "drafting":
        return <DraftPreview state={state} />;
      case "review":
        return <ReviewReport review={state.review} revisionCount={state.revision_count} />;
      case "citation":
        return <GroundingView state={state} />;
      case "formatter":
        return <ManuscriptView doc={state.final_document} />;
    }
  };

  const stateSummary = useMemo(
    () =>
      (["corpus", "themes", "blueprint", "draft", "review", "final_document"] as (keyof PipelineResult)[])
        .filter(hasKey)
        .join(", ") || "empty",
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Multi-agent runtime"
        title="Agent Hub"
        subtitle="Run any agent on its own — no need to fire the whole pipeline. Each agent reads from a shared state, so you can run just Drafting, just Review, or fan several out at once."
      />

      <SectionCard
        title="Shared inputs"
        description="Used by agents that need them (Search, Outline). Agents run independently and merge their output into the shared state."
        actions={<Badge>{`state: ${stateSummary}`}</Badge>}
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
        </div>

        <details className="mt-4 rounded-xl border border-zinc-800/70 bg-zinc-950/40 px-3 py-2">
          <summary className="cursor-pointer text-xs text-zinc-400">
            Advanced: inject shared state (paste a blueprint / corpus to run a downstream agent directly)
          </summary>
          <div className="mt-2 space-y-2">
            <textarea
              className="h-32 w-full rounded-lg border border-zinc-800 bg-zinc-950/70 p-2 font-mono text-[11px] text-zinc-200 outline-none focus:border-indigo-400/60"
              value={stateText}
              onChange={(e) => setStateText(e.target.value)}
              placeholder='{"blueprint": {...}, "corpus": [...]}'
            />
            <div className="flex items-center gap-2">
              <button
                onClick={applyStateText}
                className="rounded-lg bg-zinc-800/70 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-700/70"
              >
                Apply to state
              </button>
              <button
                onClick={() => setStateText(JSON.stringify(state, null, 2))}
                className="rounded-lg bg-zinc-800/70 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-700/70"
              >
                Load current state
              </button>
              <button
                onClick={() => setState({})}
                className="rounded-lg bg-zinc-800/70 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-700/70"
              >
                Clear state
              </button>
              {stateErr && <span className="text-xs text-rose-300">{stateErr}</span>}
            </div>
          </div>
        </details>
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        {AGENTS.map((agent) => {
          const missing = agent.requires.filter((r) => !hasKey(r));
          const ready = missing.length === 0;
          return (
            <SectionCard
              key={agent.id}
              title={agent.title}
              description={agent.description}
              actions={
                ready ? (
                  <Badge tone="success">ready</Badge>
                ) : (
                  <Badge tone="warning">{`needs ${missing.join(", ")}`}</Badge>
                )
              }
            >
              <button
                onClick={() => runAgent(agent)}
                disabled={loading[agent.id]}
                className="mb-3 rounded-xl border border-indigo-400/45 bg-indigo-500/20 px-4 py-2 text-sm font-medium text-indigo-100 transition hover:bg-indigo-500/30 disabled:opacity-50"
              >
                {loading[agent.id] ? "Running…" : `Run ${agent.title}`}
              </button>
              {errors[agent.id] && (
                <p className="mb-2 text-xs text-rose-300">{errors[agent.id]}</p>
              )}
              <div className="max-h-80 overflow-auto">{renderOutput(agent.id)}</div>
            </SectionCard>
          );
        })}
      </div>
    </div>
  );
}

function DraftPreview({ state }: { state: PipelineResult }) {
  const sections = state.draft?.sections;
  if (!sections) return <p className="text-sm text-zinc-500">No draft yet.</p>;
  return (
    <div className="space-y-2">
      {state.draft?.method && (
        <div className="text-xs text-zinc-500">generator: {state.draft.method}</div>
      )}
      {Object.entries(sections).map(([name, text]) => (
        <details key={name} className="rounded-xl border border-zinc-800/80 bg-zinc-950/50 px-3 py-2">
          <summary className="cursor-pointer text-sm font-medium text-zinc-100">
            {name} <span className="text-xs text-zinc-500">· {text.split(/\s+/).length}w</span>
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-300">{text}</p>
        </details>
      ))}
    </div>
  );
}

function GroundingView({ state }: { state: PipelineResult }) {
  const cited = (state.draft as { cited?: { grounding?: Record<string, unknown> } } | undefined)?.cited;
  const g = cited?.grounding as
    | { total_claims?: number; grounded?: number; blocked?: unknown[]; export_ready?: boolean }
    | undefined;
  if (!g) return <p className="text-sm text-zinc-500">No grounding run yet.</p>;
  return (
    <div className="space-y-1 text-sm text-zinc-300">
      <div className="flex items-center gap-2">
        <Badge tone={g.export_ready ? "success" : "warning"}>
          {g.export_ready ? "export ready" : "blocked claims"}
        </Badge>
      </div>
      <div className="text-xs text-zinc-400">
        {g.grounded ?? 0}/{g.total_claims ?? 0} factual claims grounded ·{" "}
        {(g.blocked?.length ?? 0)} blocked
      </div>
    </div>
  );
}
