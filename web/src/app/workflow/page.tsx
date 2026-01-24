"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type {
  ComprehensiveSummary,
  Draft,
  Paper,
  PlagiarismReport,
  QueryResult,
} from "@/lib/types";

type StepId = "topic" | "retrieval" | "summary" | "draft" | "plagiarism";

export default function WorkflowPage() {
  const [topic, setTopic] = useState("");
  const [topKeywords, setTopKeywords] = useState(8);
  const [maxPapers, setMaxPapers] = useState(5);

  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [summary, setSummary] = useState<ComprehensiveSummary | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [plagiarism, setPlagiarism] = useState<PlagiarismReport | null>(null);

  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<"ok" | "down" | "checking">(
    "checking",
  );
  const [copied, setCopied] = useState<string | null>(null);
  const [openStep, setOpenStep] = useState<StepId>("topic");

  const keywords = useMemo(() => queryResult?.keywords ?? [], [queryResult]);

  useEffect(() => {
    let mounted = true;
    api
      .health()
      .then(() => mounted && setApiStatus("ok"))
      .catch(() => mounted && setApiStatus("down"));
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(null), 1200);
    return () => clearTimeout(t);
  }, [copied]);

  const getErrorMessage = (e: unknown) =>
    e instanceof Error ? e.message : "Request failed";

  const downloadJson = (data: unknown, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadText = (text: string, filename: string) => {
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
    } catch {
      setError("Copy failed");
    }
  };

  const stats = useMemo(() => {
    const totalPapers = papers.length;
    const summarySections = summary
      ? Object.keys(summary.section_summaries || {}).length
      : 0;
    const insights = (summary?.key_insights ?? {}) as Record<string, string[]>;
    const insightsCount = Object.values(insights).reduce(
      (acc, arr) => acc + arr.length,
      0,
    );
    const draftWords = draft
      ? draft.abstract.split(" ").length +
        draft.introduction.split(" ").length +
        draft.related_work.split(" ").length
      : 0;
    const plagiarismScore = plagiarism?.overall_score ?? null;
    return {
      totalPapers,
      summarySections,
      insightsCount,
      draftWords,
      plagiarismScore,
    };
  }, [papers, summary, draft, plagiarism]);

  const isComplete = {
    topic: !!queryResult,
    retrieval: papers.length > 0,
    summary: !!summary,
    draft: !!draft,
    plagiarism: !!plagiarism,
  } as const;

  const stepOrder: StepId[] = [
    "topic",
    "retrieval",
    "summary",
    "draft",
    "plagiarism",
  ];
  const currentStep =
    stepOrder.find((step) => !isComplete[step]) ?? "plagiarism";

  useEffect(() => {
    setOpenStep(currentStep);
  }, [currentStep]);

  const handleQuery = async () => {
    setError(null);
    setLoading("Analyzing topic...");
    try {
      const result = await api.query({
        text: topic,
        top_keywords: topKeywords,
      });
      setQueryResult(result);
      setPapers([]);
      setSummary(null);
      setDraft(null);
      setPlagiarism(null);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const handleRetrieve = async () => {
    setError(null);
    setLoading("Retrieving papers...");
    try {
      const result = await api.retrieve({
        keywords,
        max_results: maxPapers,
        use_multi_query: true,
        subtopics: queryResult?.subtopics,
      });
      setPapers(result);
      setSummary(null);
      setDraft(null);
      setPlagiarism(null);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const handleSummarize = async () => {
    setError(null);
    setLoading("Summarizing papers...");
    try {
      const result = await api.summarize({ papers, keywords });
      setSummary(result);
      setDraft(null);
      setPlagiarism(null);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const handleDraft = async () => {
    if (!summary) return;
    setError(null);
    setLoading("Generating draft...");
    try {
      const result = await api.draft({
        research_topic: topic,
        comprehensive_summary: summary,
        keywords,
        config: {
          max_new_tokens: 700,
          min_new_tokens: 350,
          temperature: 0.7,
          top_p: 0.9,
        },
      });
      setDraft(result);
      setPlagiarism(null);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const handlePlagiarism = async () => {
    if (!draft) return;
    setError(null);
    setLoading("Checking plagiarism...");
    try {
      const result = await api.plagiarism({
        generated_draft: draft,
        source_papers: papers,
        research_topic: topic,
      });
      setPlagiarism(result);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const StepShell = ({
    step,
    title,
    description,
    children,
  }: {
    step: StepId;
    title: string;
    description: string;
    children: ReactNode;
  }) => {
    const completed = isComplete[step];
    const isOpen = openStep === step;

    if (!completed && step !== currentStep) return null;

    return (
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm font-semibold">{title}</div>
            <p className="text-xs text-zinc-400">{description}</p>
          </div>
          <div className="flex items-center gap-2">
            {completed ? (
              <Badge tone="success">Completed</Badge>
            ) : (
              <Badge tone="warning">In progress</Badge>
            )}
            <button
              onClick={() => setOpenStep(isOpen ? currentStep : step)}
              className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              {isOpen ? "Collapse" : "Expand"}
            </button>
          </div>
        </div>
        {isOpen && <div className="mt-4">{children}</div>}
      </div>
    );
  };

  return (
    <div className="space-y-6 px-2 md:px-4">
      <PageHeader
        title="Workflow"
        subtitle="Complete one agent at a time. Each card unlocks the next step."
        actions={
          <div className="flex items-center gap-3">
            <Badge
              tone={
                apiStatus === "ok"
                  ? "success"
                  : apiStatus === "down"
                    ? "danger"
                    : "warning"
              }
            >
              {apiStatus === "ok" && "API Online"}
              {apiStatus === "down" && "API Offline"}
              {apiStatus === "checking" && "Checking API..."}
            </Badge>
            <Badge tone="info">{copied ? `Copied ${copied}` : "Ready"}</Badge>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Papers"
          value={stats.totalPapers}
          caption="Retrieved sources"
        />
        <StatCard
          label="Summary sections"
          value={stats.summarySections}
          caption="Structured outputs"
        />
        <StatCard
          label="Insights"
          value={stats.insightsCount}
          caption="Extracted signals"
        />
        <StatCard
          label="Draft words"
          value={stats.draftWords}
          caption="Academic length"
        />
      </section>

      <SectionCard
        title="Agent pipeline"
        description="Only one active card at a time."
      >
        <div className="space-y-4">
          <StepShell
            step="topic"
            title="1) Topic analysis"
            description="Define the topic and extract keywords."
          >
            <div className="space-y-3">
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., LLMs in healthcare"
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-4 py-2 text-sm"
              />
              <div className="flex items-center gap-3">
                <label className="text-sm text-zinc-400">Keywords</label>
                <input
                  type="number"
                  value={topKeywords}
                  min={3}
                  max={20}
                  onChange={(e) => setTopKeywords(Number(e.target.value))}
                  className="w-24 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
                />
              </div>
              <button
                onClick={handleQuery}
                disabled={!topic || !!loading}
                className="w-full rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium hover:bg-indigo-400 disabled:opacity-50"
              >
                Analyze Topic
              </button>
              {queryResult && (
                <div className="rounded-xl bg-zinc-950 p-3 text-xs text-zinc-300">
                  Keywords: {queryResult.keywords.join(", ")}
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            step="retrieval"
            title="2) Paper retrieval"
            description="Fetch and review relevant papers."
          >
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <label className="text-sm text-zinc-400">Max papers</label>
                <input
                  type="number"
                  value={maxPapers}
                  min={1}
                  max={20}
                  onChange={(e) => setMaxPapers(Number(e.target.value))}
                  className="w-24 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
                />
              </div>
              <button
                onClick={handleRetrieve}
                disabled={!keywords.length || !!loading}
                className="w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium hover:bg-emerald-400 disabled:opacity-50"
              >
                Retrieve Papers
              </button>
              {papers.length > 0 && (
                <div className="space-y-2 text-xs text-zinc-300">
                  {papers.map((paper, idx) => (
                    <div
                      key={idx}
                      className="rounded-lg border border-zinc-800 bg-zinc-950 p-3"
                    >
                      {(paper as { title?: string }).title || "Untitled"}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            step="summary"
            title="3) Summary synthesis"
            description="Generate the comprehensive summary."
          >
            <div className="space-y-3">
              <button
                onClick={handleSummarize}
                disabled={!papers.length || !!loading}
                className="w-full rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium hover:bg-cyan-400 disabled:opacity-50"
              >
                Summarize
              </button>
              {summary && (
                <div className="rounded-xl bg-zinc-950 p-3 text-xs text-zinc-300">
                  <div className="flex items-center justify-between">
                    <span>Summary ready</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            JSON.stringify(summary, null, 2),
                            "summary",
                          )
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Copy JSON
                      </button>
                      <button
                        onClick={() =>
                          summary &&
                          downloadJson(summary, "comprehensive_summary.json")
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Export JSON
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 space-y-3 rounded-lg border border-zinc-800 bg-black/40 p-3 text-xs text-zinc-200">
                    {summary.executive_summary && (
                      <div>
                        <div className="text-[11px] uppercase text-zinc-500">
                          Executive Summary
                        </div>
                        <p className="mt-1 text-zinc-200">
                          {summary.executive_summary as string}
                        </p>
                      </div>
                    )}

                    {summary.section_summaries && (
                      <div className="space-y-2">
                        <div className="text-[11px] uppercase text-zinc-500">
                          Section Summaries
                        </div>
                        {Object.entries(
                          summary.section_summaries as Record<string, string>,
                        ).map(([section, content]) => (
                          <div
                            key={section}
                            className="rounded-md border border-zinc-800/60 bg-zinc-900/50 p-2"
                          >
                            <div className="text-[11px] uppercase text-zinc-500">
                              {section}
                            </div>
                            <p className="mt-1 text-zinc-200">{content}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {summary.key_insights && (
                      <div className="space-y-2">
                        <div className="text-[11px] uppercase text-zinc-500">
                          Key Insights
                        </div>
                        {Object.entries(
                          summary.key_insights as Record<string, string[]>,
                        ).map(([group, items]) => (
                          <div
                            key={group}
                            className="rounded-md border border-zinc-800/60 bg-zinc-900/50 p-2"
                          >
                            <div className="text-[11px] uppercase text-zinc-500">
                              {group.replace(/_/g, " ")}
                            </div>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-zinc-200">
                              {items.map((item) => (
                                <li key={item}>{item}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            step="draft"
            title="4) Draft generation"
            description="Turn synthesis into draft sections."
          >
            <div className="space-y-3">
              <button
                onClick={handleDraft}
                disabled={!summary || !!loading}
                className="w-full rounded-lg bg-fuchsia-500 px-4 py-2 text-sm font-medium hover:bg-fuchsia-400 disabled:opacity-50"
              >
                Generate Draft
              </button>
              {draft && (
                <div className="rounded-xl bg-zinc-950 p-3 text-xs text-zinc-300">
                  <div className="flex items-center justify-between">
                    <span>Draft ready</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `Abstract\n${draft.abstract}\n\nIntroduction\n${draft.introduction}\n\nRelated Work\n${draft.related_work}`,
                            "draft",
                          )
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Copy
                      </button>
                      <button
                        onClick={() =>
                          downloadText(
                            `Abstract\n${draft.abstract}\n\nIntroduction\n${draft.introduction}\n\nRelated Work\n${draft.related_work}`,
                            "draft.txt",
                          )
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Export TXT
                      </button>
                    </div>
                  </div>
                  <div className="mt-3 space-y-3">
                    <div>
                      <div className="text-[11px] uppercase text-zinc-500">
                        Abstract
                      </div>
                      <p className="mt-1 text-xs text-zinc-200">
                        {draft.abstract}
                      </p>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase text-zinc-500">
                        Introduction
                      </div>
                      <p className="mt-1 text-xs text-zinc-200">
                        {draft.introduction}
                      </p>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase text-zinc-500">
                        Related Work
                      </div>
                      <p className="mt-1 text-xs text-zinc-200">
                        {draft.related_work}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            step="plagiarism"
            title="5) Plagiarism check"
            description="Validate originality against sources."
          >
            <div className="space-y-3">
              <button
                onClick={handlePlagiarism}
                disabled={!draft || !!loading}
                className="w-full rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium hover:bg-amber-400 disabled:opacity-50"
              >
                Run Check
              </button>
              {plagiarism && (
                <div className="rounded-xl bg-zinc-950 p-3 text-xs text-zinc-300">
                  <div className="flex items-center justify-between">
                    <span>
                      Score: {plagiarism.overall_score?.toFixed(1) ?? "0"}%
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            JSON.stringify(plagiarism, null, 2),
                            "report",
                          )
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Copy JSON
                      </button>
                      <button
                        onClick={() =>
                          downloadJson(plagiarism, "plagiarism_report.json")
                        }
                        className="rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Export JSON
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </StepShell>
        </div>
      </SectionCard>

      <SectionCard
        title="Pipeline status"
        description="Live updates from the workflow."
      >
        <div className="space-y-2 text-sm">
          {loading && <div className="text-indigo-300">{loading}</div>}
          {error && <div className="text-rose-400">{error}</div>}
          {!loading && !error && <div className="text-zinc-500">Idle</div>}
        </div>
      </SectionCard>
    </div>
  );
}
