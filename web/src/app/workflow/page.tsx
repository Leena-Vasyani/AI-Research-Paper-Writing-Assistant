"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Badge from "@/components/Badge";
import PageHeader from "@/components/PageHeader";
import SectionCard from "@/components/SectionCard";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";
import type {
  CitationCandidate,
  ComprehensiveSummary,
  Draft,
  Paper,
  PlagiarismReport,
  QueryResult,
} from "@/lib/types";

type StepId = "topic" | "retrieval" | "summary" | "draft" | "plagiarism";

function StepShell({
  step,
  title,
  description,
  children,
  isComplete,
  openStep,
  currentStep,
  setOpenStep,
}: {
  step: StepId;
  title: string;
  description: string;
  children: ReactNode;
  isComplete: Record<StepId, boolean>;
  openStep: StepId;
  currentStep: StepId;
  setOpenStep: (step: StepId) => void;
}) {
  const completed = isComplete[step];
  const isOpen = openStep === step;

  if (!completed && step !== currentStep) return null;

  return (
    <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-5 backdrop-blur-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-[14px] font-semibold tracking-wide text-zinc-100">{title}</h3>
          <p className="mt-0.5 text-[12px] leading-relaxed text-zinc-500">{description}</p>
        </div>
        <div className="flex items-center gap-2">
          {completed ? (
            <Badge tone="success">Completed</Badge>
          ) : (
            <Badge tone="warning">In progress</Badge>
          )}
          <button
            onClick={() => setOpenStep(isOpen ? currentStep : step)}
            className="rounded-lg border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          >
            {isOpen ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>
      {isOpen && <div className="mt-5">{children}</div>}
    </div>
  );
}

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
  const [citationClaim, setCitationClaim] = useState("");
  const [citationStyle, setCitationStyle] = useState<"apa" | "ieee" | "mla">(
    "ieee",
  );
  const [citationCandidates, setCitationCandidates] = useState<
    CitationCandidate[]
  >([]);
  const [citationInfo, setCitationInfo] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [customKeyword, setCustomKeyword] = useState("");

  useEffect(() => {
    if (queryResult?.keywords) {
      setKeywords(queryResult.keywords);
    }
  }, [queryResult]);

  const addCustomKeyword = () => {
    const kw = customKeyword.trim().toLowerCase();
    if (!kw || keywords.includes(kw)) return;
    setKeywords((prev) => [...prev, kw]);
    setCustomKeyword("");
  };

  const removeKeyword = (kw: string) => {
    setKeywords((prev) => prev.filter((k) => k !== kw));
  };

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
      // /api/retrieve returns { papers, domain, source_status, ... }
      setPapers(Array.isArray(result) ? result : result?.papers ?? []);
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

  const handleSuggestCitation = async () => {
    const claim = citationClaim.trim();
    if (!claim) {
      setError("Enter a claim sentence to suggest citations.");
      return;
    }
    setError(null);
    setLoading("Suggesting citations...");
    setCitationInfo(null);
    try {
      const result = await api.suggestCitation({
        claim_text: claim,
        citation_style: citationStyle,
        max_candidates: 3,
        keywords,
        provided_papers: papers,
        auto_retrieve: papers.length === 0,
        retrieve_max_results: 8,
      });
      setCitationCandidates(result.candidates ?? []);
      const noteText = result.notes?.length ? ` • ${result.notes[0]}` : "";
      setCitationInfo(
        `Found ${result.candidates?.length ?? 0} candidate(s) with confidence ${Math.round((result.confidence ?? 0) * 100)}%${noteText}`,
      );
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(null);
    }
  };

  const stepShellProps = { isComplete, openStep, currentStep, setOpenStep };

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
            {...stepShellProps}
            step="topic"
            title="1) Topic analysis"
            description="Define the topic and extract keywords."
          >
            <div className="space-y-4">
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g., LLMs in healthcare"
                className="w-full rounded-lg border border-zinc-700/60 bg-zinc-950 px-4 py-2.5 text-[13px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors"
              />
              <div className="flex items-center gap-4">
                <label className="text-[13px] font-medium tracking-wide text-zinc-400">
                  Keywords to extract
                </label>
                <input
                  type="number"
                  value={topKeywords}
                  min={3}
                  max={20}
                  onChange={(e) => setTopKeywords(Number(e.target.value))}
                  className="w-24 rounded-lg border border-zinc-700/60 bg-zinc-950 px-3 py-2 text-[13px] font-medium text-zinc-200 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                />
              </div>
              <button
                onClick={handleQuery}
                disabled={!topic || !!loading}
                className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-[13px] font-semibold tracking-wide text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Analyze Topic
              </button>
              {queryResult && (
                <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/80 p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
                    Keywords
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {keywords.map((kw) => (
                      <span
                        key={kw}
                        className="group/kw inline-flex items-center gap-1 rounded-full border border-indigo-800/40 bg-indigo-950/40 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300"
                      >
                        {kw}
                        <button
                          type="button"
                          onClick={() => removeKeyword(kw)}
                          className="ml-0.5 rounded-full p-0.5 text-indigo-400/60 hover:bg-indigo-800/40 hover:text-indigo-200 transition-colors"
                          aria-label={`Remove ${kw}`}
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <input
                      value={customKeyword}
                      onChange={(e) => setCustomKeyword(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          addCustomKeyword();
                        }
                      }}
                      placeholder="Add a keyword…"
                      className="flex-1 rounded-lg border border-zinc-700/60 bg-zinc-900 px-3 py-1.5 text-[12px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={addCustomKeyword}
                      disabled={!customKeyword.trim()}
                      className="rounded-lg bg-indigo-600/80 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      Add
                    </button>
                  </div>
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            {...stepShellProps}
            step="retrieval"
            title="2) Paper retrieval"
            description="Fetch and review relevant papers from arXiv, OpenAlex, and Semantic Scholar."
          >
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <label className="text-[13px] font-medium tracking-wide text-zinc-400">
                  Maximum papers
                </label>
                <input
                  type="number"
                  value={maxPapers}
                  min={1}
                  max={20}
                  onChange={(e) => setMaxPapers(Number(e.target.value))}
                  className="w-24 rounded-lg border border-zinc-700/60 bg-zinc-950 px-3 py-2 text-[13px] font-medium text-zinc-200 focus:border-emerald-500/60 focus:outline-none focus:ring-1 focus:ring-emerald-500/30 transition-colors"
                />
              </div>
              <button
                onClick={handleRetrieve}
                disabled={!keywords.length || !!loading}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-[13px] font-semibold tracking-wide text-white hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Retrieve Papers
              </button>

              {papers.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-semibold tracking-wide text-zinc-300">
                      {papers.length} paper{papers.length !== 1 ? "s" : ""}{" "}
                      retrieved
                    </p>
                    <button
                      onClick={() =>
                        downloadJson(papers, "retrieved_papers.json")
                      }
                      className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                    >
                      Export All
                    </button>
                  </div>

                  {papers.map((paper, idx) => {
                    const title =
                      (paper as { title?: string }).title || "Untitled";
                    const authors =
                      (paper as { authors_str?: string }).authors_str || "";
                    const published =
                      (paper as { published?: string }).published || "";
                    const source =
                      (paper as { source?: string }).source || "unknown";
                    const relevance =
                      (paper as { relevance_score?: number })
                        .relevance_score ?? 0;
                    const abstract =
                      (paper as { abstract?: string }).abstract || "";
                    const pdfUrl =
                      (paper as { pdf_url?: string }).pdf_url || "";
                    const entryId =
                      (paper as { entry_id?: string }).entry_id || "";
                    const categories =
                      (paper as { categories?: string[] }).categories || [];
                    const primaryCategory =
                      (paper as { primary_category?: string })
                        .primary_category || "";

                    const relevancePct = Math.round(relevance * 100);
                    const relevanceColor =
                      relevancePct >= 80
                        ? "bg-emerald-500"
                        : relevancePct >= 60
                          ? "bg-amber-500"
                          : "bg-rose-500";
                    const sourceLabel =
                      source === "arxiv"
                        ? "arXiv"
                        : source === "openalex"
                          ? "OpenAlex"
                          : source === "semantic_scholar"
                            ? "Semantic Scholar"
                            : source;
                    const sourceBadgeColor =
                      source === "arxiv"
                        ? "border-red-700/40 bg-red-950/50 text-red-300"
                        : source === "openalex"
                          ? "border-orange-700/40 bg-orange-950/50 text-orange-300"
                          : "border-blue-700/40 bg-blue-950/50 text-blue-300";

                    return (
                      <div
                        key={entryId || idx}
                        className="group rounded-xl border border-zinc-800/80 bg-zinc-950/80 p-4 transition-colors hover:border-zinc-700/70"
                      >
                        {/* Header row: index + title + source badge */}
                        <div className="flex items-start gap-3">
                          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-zinc-800 text-[11px] font-bold text-zinc-400">
                            {idx + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <h4 className="text-[13px] font-semibold leading-snug text-zinc-100">
                              {title}
                            </h4>

                            {/* Authors */}
                            {authors && (
                              <p className="mt-1 text-[12px] leading-relaxed text-zinc-400">
                                {authors}
                              </p>
                            )}

                            {/* Meta row: date · source · category */}
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
                              {published && (
                                <span className="font-medium">
                                  {published}
                                </span>
                              )}
                              {published && <span className="opacity-40">·</span>}
                              <span
                                className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${sourceBadgeColor}`}
                              >
                                {sourceLabel}
                              </span>
                              {primaryCategory &&
                                primaryCategory !== source && (
                                  <>
                                    <span className="opacity-40">·</span>
                                    <span className="font-medium text-zinc-500">
                                      {primaryCategory}
                                    </span>
                                  </>
                                )}
                            </div>
                          </div>
                        </div>

                        {/* Relevance bar */}
                        <div className="mt-3 flex items-center gap-2">
                          <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                            Relevance
                          </span>
                          <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${relevanceColor} transition-all`}
                              style={{ width: `${relevancePct}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-bold tabular-nums text-zinc-300">
                            {relevancePct}%
                          </span>
                        </div>

                        {/* Abstract snippet */}
                        {abstract && (
                          <p className="mt-3 text-[12px] leading-[1.6] text-zinc-400 line-clamp-3">
                            {abstract.length > 320
                              ? `${abstract.slice(0, 320)}…`
                              : abstract}
                          </p>
                        )}

                        {/* Categories */}
                        {categories.length > 0 &&
                          categories.some((c) => c) && (
                            <div className="mt-2.5 flex flex-wrap gap-1.5">
                              {categories
                                .filter((c) => c)
                                .slice(0, 5)
                                .map((cat) => (
                                  <span
                                    key={cat}
                                    className="rounded-md border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-[10px] font-medium text-zinc-500"
                                  >
                                    {cat}
                                  </span>
                                ))}
                            </div>
                          )}

                        {/* Action row */}
                        <div className="mt-3 flex items-center gap-2 border-t border-zinc-800/60 pt-3">
                          {pdfUrl && (
                            <a
                              href={pdfUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-700/50 px-2 py-1 text-[11px] font-medium text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
                            >
                              <svg
                                className="h-3 w-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                />
                              </svg>
                              PDF
                            </a>
                          )}
                          {entryId && (
                            <a
                              href={entryId}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-zinc-700/50 px-2 py-1 text-[11px] font-medium text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
                            >
                              <svg
                                className="h-3 w-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                strokeWidth={2}
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                />
                              </svg>
                              Source
                            </a>
                          )}
                          <button
                            onClick={() =>
                              copyToClipboard(title, `paper-${idx + 1}`)
                            }
                            className="ml-auto rounded-md border border-zinc-700/50 px-2 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                          >
                            Copy title
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            {...stepShellProps}
            step="summary"
            title="3) Summary synthesis"
            description="Generate the comprehensive summary."
          >
            <div className="space-y-4">
              <button
                onClick={handleSummarize}
                disabled={!papers.length || !!loading}
                className="w-full rounded-lg bg-cyan-600 px-4 py-2.5 text-[13px] font-semibold tracking-wide text-white hover:bg-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Summarize
              </button>
              {summary && (
                <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/80 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-semibold tracking-wide text-zinc-300">Summary ready</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            JSON.stringify(summary, null, 2),
                            "summary",
                          )
                        }
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                      >
                        Copy JSON
                      </button>
                      <button
                        onClick={() =>
                          summary &&
                          downloadJson(summary, "comprehensive_summary.json")
                        }
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                      >
                        Export JSON
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 space-y-3 rounded-lg border border-zinc-800/50 bg-black/30 p-4 text-[12px] leading-[1.6] text-zinc-200">
                    {typeof summary.executive_summary === "string" &&
                      summary.executive_summary.trim() && (
                        <div>
                          <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                            Executive Summary
                          </p>
                          <p className="mt-1.5 text-[12px] leading-[1.7] text-zinc-300">
                            {summary.executive_summary}
                          </p>
                        </div>
                      )}

                    {summary.section_summaries && (
                      <div className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                          Section Summaries
                        </p>
                        {Object.entries(
                          summary.section_summaries as Record<string, string>,
                        ).map(([section, content]) => (
                          <div
                            key={section}
                            className="rounded-md border border-zinc-800/60 bg-zinc-900/50 p-2"
                          >
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                              {section}
                            </p>
                            <p className="mt-1.5 text-[12px] leading-[1.7] text-zinc-300">{content}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {summary.key_insights && (
                      <div className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                          Key Insights
                        </p>
                        {Object.entries(
                          summary.key_insights as Record<string, string[]>,
                        ).map(([group, items]) => (
                          <div
                            key={group}
                            className="rounded-md border border-zinc-800/60 bg-zinc-900/50 p-2"
                          >
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                              {group.replace(/_/g, " ")}
                            </p>
                            <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[12px] leading-[1.6] text-zinc-300">
                              {items.map((item) => (
                                <li key={String(item)}>{String(item)}</li>
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
            {...stepShellProps}
            step="draft"
            title="4) Draft generation"
            description="Turn synthesis into draft sections."
          >
            <div className="space-y-4">
              <button
                onClick={handleDraft}
                disabled={!summary || !!loading}
                className="w-full rounded-lg bg-fuchsia-600 px-4 py-2.5 text-[13px] font-semibold tracking-wide text-white hover:bg-fuchsia-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Generate Draft
              </button>
              {draft && (
                <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/80 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-semibold tracking-wide text-zinc-300">Draft ready</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            `Abstract\n${draft.abstract}\n\nIntroduction\n${draft.introduction}\n\nRelated Work\n${draft.related_work}`,
                            "draft",
                          )
                        }
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
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
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                      >
                        Export TXT
                      </button>
                    </div>
                  </div>
                  <div className="mt-4 space-y-4">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                        Abstract
                      </p>
                      <p className="mt-1.5 text-[12px] leading-[1.7] text-zinc-300">
                        {draft.abstract}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                        Introduction
                      </p>
                      <p className="mt-1.5 text-[12px] leading-[1.7] text-zinc-300">
                        {draft.introduction}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                        Related Work
                      </p>
                      <p className="mt-1.5 text-[12px] leading-[1.7] text-zinc-300">
                        {draft.related_work}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </StepShell>

          <StepShell
            {...stepShellProps}
            step="plagiarism"
            title="5) Plagiarism check"
            description="Validate originality against sources."
          >
            <div className="space-y-4">
              <button
                onClick={handlePlagiarism}
                disabled={!draft || !!loading}
                className="w-full rounded-lg bg-amber-600 px-4 py-2.5 text-[13px] font-semibold tracking-wide text-white hover:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Run Check
              </button>
              {plagiarism && (
                <div className="rounded-xl border border-zinc-800/60 bg-zinc-950/80 p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-semibold tracking-wide text-zinc-300">
                      Score: {plagiarism.overall_score?.toFixed(1) ?? "0"}%
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          copyToClipboard(
                            JSON.stringify(plagiarism, null, 2),
                            "report",
                          )
                        }
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
                      >
                        Copy JSON
                      </button>
                      <button
                        onClick={() =>
                          downloadJson(plagiarism, "plagiarism_report.json")
                        }
                        className="rounded-md border border-zinc-700/60 px-2.5 py-1 text-[11px] font-medium text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
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

      <SectionCard
        title="Citation assistant"
        description="Suggest citations for a claim using retrieved papers and RAG fallback."
      >
        <div className="space-y-3">
          <textarea
            value={citationClaim}
            onChange={(e) => setCitationClaim(e.target.value)}
            rows={3}
            placeholder="Enter a claim sentence, e.g., Transformer models improve long-context reasoning under retrieval augmentation."
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
          />
          <div className="flex items-center gap-3">
            <label className="text-xs text-zinc-400">Style</label>
            <select
              value={citationStyle}
              onChange={(e) =>
                setCitationStyle(e.target.value as "apa" | "ieee" | "mla")
              }
              className="rounded-lg border border-zinc-800 bg-zinc-950 px-2 py-1 text-xs"
            >
              <option value="ieee">IEEE</option>
              <option value="apa">APA</option>
              <option value="mla">MLA</option>
            </select>
            <button
              onClick={handleSuggestCitation}
              disabled={!citationClaim.trim() || !!loading}
              className="rounded-lg bg-cyan-500 px-3 py-1 text-xs font-medium hover:bg-cyan-400 disabled:opacity-50"
            >
              Suggest citation
            </button>
          </div>
          {citationInfo && (
            <div className="text-xs text-cyan-300">{citationInfo}</div>
          )}
          {!!citationCandidates.length && (
            <div className="space-y-2">
              {citationCandidates.map((candidate, idx) => (
                <div
                  key={`${candidate.title}-${idx}`}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs"
                >
                  <div className="text-zinc-200">
                    [{idx + 1}] {candidate.title || "Untitled"}
                  </div>
                  <div className="mt-1 text-zinc-400">
                    {candidate.authors || "Unknown authors"} •{" "}
                    {candidate.year || "n.d."} •{" "}
                    {Math.round((candidate.relevance_score || 0) * 100)}%
                  </div>
                  <div className="mt-1 text-zinc-300">{candidate.in_text}</div>
                  <div className="mt-1 text-zinc-500 break-all">
                    {candidate.reference}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
