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
  DraftPreview,
  ManuscriptView,
  QAView,
  ReviewReport,
  ThemesView,
} from "@/components/pipeline/PipelineCards";
import HumanizePanel from "@/components/pipeline/HumanizePanel";
import FieldSelector from "@/components/FieldSelector";
import { DEFAULT_FIELD_ID, getField } from "@/lib/fields";

type Stage =
  | "search"
  | "topic_mining"
  | "qa"
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
  { id: "qa", title: "Research Q&A", description: "Pose research-level questions and answer them from the corpus (feeds the Introduction & Related Work).", requires: ["corpus"], outputs: ["qa"] },
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
  const [field, setField] = useState(DEFAULT_FIELD_ID);
  const [subfield, setSubfield] = useState("");
  const [venue, setVenue] = useState("IEEE");
  const [outputType, setOutputType] = useState("research_paper");
  const [maxResults, setMaxResults] = useState(8);

  const [humanizeOn, setHumanizeOn] = useState(true);
  const [humanizeFraction, setHumanizeFraction] = useState(0.4);

  const [state, setState] = useState<PipelineResult>({});
  const [loading, setLoading] = useState<Record<Stage, boolean>>({} as Record<Stage, boolean>);
  const [errors, setErrors] = useState<Record<Stage, string>>({} as Record<Stage, string>);
  const [stateText, setStateText] = useState("");
  const [stateErr, setStateErr] = useState<string | null>(null);
  // Soft gate: the generated draft must be humanized before Review/Citation run.
  const [draftHumanized, setDraftHumanized] = useState(false);

  // Field change resets the subfield and applies the discipline's default venue.
  const handleFieldChange = (f: string, s: string) => {
    setSubfield(s);
    if (f !== field) {
      setField(f);
      setVenue(getField(f).defaults.venue);
    }
  };

  const hasKey = (k: keyof PipelineResult): boolean => {
    const v = state[k];
    if (v == null) return false;
    if (Array.isArray(v)) return v.length > 0;
    if (typeof v === "object") return Object.keys(v).length > 0;
    return true;
  };

  const runAgent = async (agent: (typeof AGENTS)[number]) => {
    // Soft gate: don't score/ground a draft the author hasn't humanized yet
    // (only when the humanization gate is enabled).
    if (
      humanizeOn &&
      (agent.id === "review" || agent.id === "citation") &&
      state.draft?.sections &&
      !draftHumanized
    ) {
      setErrors((e) => ({
        ...e,
        [agent.id]: "Humanize the draft first (Drafting card) to reduce plagiarism.",
      }));
      return;
    }
    setErrors((e) => ({ ...e, [agent.id]: "" }));
    setLoading((l) => ({ ...l, [agent.id]: true }));
    try {
      const base: Record<string, unknown> = {
        ...(state as Record<string, unknown>),
        topic,
        target_venue: venue,
        output_type: outputType,
        constraints: { max_results: maxResults, humanize_fraction: humanizeFraction, field, subfield },
      };
      const res = await api.runStage({ stage: agent.id, state: base });
      if (agent.id === "drafting") setDraftHumanized(false);
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
      setDraftHumanized(false);
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
      case "qa":
        return <QAView qa={state.qa} />;
      case "outline":
        return <BlueprintView blueprint={state.blueprint} />;
      case "drafting":
        if (!state.draft?.sections) return <DraftPreview draft={state.draft} />;
        if (humanizeOn && !draftHumanized)
          return (
            <HumanizePanel
              draft={state.draft}
              state={state}
              fraction={humanizeFraction}
              confirmLabel="Confirm humanization — unlock Review & Citation"
              onConfirm={(edited) => {
                setState((prev) => ({ ...prev, draft: { ...prev.draft, sections: edited } }));
                setDraftHumanized(true);
              }}
            />
          );
        return (
          <div className="space-y-2">
            {humanizeOn ? (
              <Badge tone="success">humanized</Badge>
            ) : (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] text-amber-200">
                Humanization off — Review & Citation run on the raw draft (higher plagiarism
                risk).
              </div>
            )}
            <DraftPreview draft={state.draft} />
          </div>
        );
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
      (["corpus", "themes", "qa", "blueprint", "draft", "review", "final_document"] as (keyof PipelineResult)[])
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
            Require manual humanization before Review &amp; Citation (cuts plagiarism)
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
                onClick={() => {
                  setState({});
                  setDraftHumanized(false);
                }}
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
