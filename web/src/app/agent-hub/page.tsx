"use client";

import { useMemo, useState } from "react";
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

const pretty = (value: unknown) => JSON.stringify(value, null, 2);

const textToPaperSeed = (text: string): Paper[] => {
  const clean = text.trim();
  if (!clean) return [];
  return [
    {
      title: "Uploaded Document",
      abstract: clean,
      authors_str: "",
      published: "",
      primary_category: "uploaded",
      source: "local_upload",
    } as Paper,
  ];
};

const extractKeywordsFromText = (text: string, max = 8): string[] => {
  const stopwords = new Set([
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "will",
    "would",
    "can",
    "could",
    "should",
    "about",
    "your",
    "their",
    "our",
    "but",
    "not",
    "than",
    "then",
    "also",
    "using",
    "used",
    "use",
    "over",
    "under",
    "between",
    "among",
    "into",
    "onto",
    "in",
    "on",
    "at",
    "to",
    "of",
    "a",
    "an",
    "is",
    "it",
    "as",
    "by",
    "or",
    "be",
    "we",
    "they",
    "you",
  ]);

  const counts = new Map<string, number>();
  const words = text.toLowerCase().match(/[a-z][a-z-]{2,}/g) ?? [];
  for (const word of words) {
    if (stopwords.has(word)) continue;
    counts.set(word, (counts.get(word) ?? 0) + 1);
  }

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, max)
    .map(([word]) => word);
};

const textToDraftSeed = (text: string): Draft => {
  const clean = text.trim();
  const words = clean.split(/\s+/).filter(Boolean);
  const chunk = Math.max(80, Math.floor(words.length / 3));
  const slice = (start: number) =>
    words
      .slice(start, start + chunk)
      .join(" ")
      .trim();

  return {
    abstract: slice(0),
    introduction: slice(chunk),
    related_work: slice(chunk * 2),
  };
};

type AgentView =
  | "all"
  | "query"
  | "retrieval"
  | "summary"
  | "draft"
  | "plagiarism";

export default function AgentHubPage() {
  const [topic, setTopic] = useState("");
  const [topKeywords, setTopKeywords] = useState(8);
  const [maxPapers, setMaxPapers] = useState(5);
  const [retrieveSources, setRetrieveSources] = useState<string[]>([
    "arxiv",
    "openalex",
    "semantic_scholar",
  ]);

  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [summary, setSummary] = useState<ComprehensiveSummary | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [plagiarism, setPlagiarism] = useState<PlagiarismReport | null>(null);

  const [keywordsInput, setKeywordsInput] = useState("");
  const [papersInput, setPapersInput] = useState("");
  const [summaryInput, setSummaryInput] = useState("");
  const [draftInput, setDraftInput] = useState("");
  const [sourcesInput, setSourcesInput] = useState("");

  const [documentText, setDocumentText] = useState("");
  const [documentWarnings, setDocumentWarnings] = useState<string[]>([]);

  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<AgentView>("all");

  const keywords = useMemo(() => {
    return keywordsInput
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
  }, [keywordsInput]);

  const stats = useMemo(
    () => ({
      keywords: keywords.length,
      papers: papers.length,
      summarySections: summary
        ? Object.keys(summary.section_summaries ?? {}).length
        : 0,
      plagiarism: plagiarism?.overall_score
        ? `${plagiarism.overall_score.toFixed(1)}%`
        : "-",
    }),
    [keywords, papers.length, summary, plagiarism],
  );

  const parseJson = <T,>(text: string): T | null => {
    if (!text.trim()) return null;
    try {
      return JSON.parse(text) as T;
    } catch {
      setError("Invalid JSON input");
      return null;
    }
  };

  const handleUploadDocument = async (file: File | null) => {
    if (!file) return;
    setError(null);
    setLoading("Extracting text from document...");
    try {
      const result = await api.extractText(file);
      setDocumentText(result.text);
      setDocumentWarnings(result.warnings ?? []);
      if (!topic.trim() && result.text.trim()) {
        setTopic(result.text.slice(0, 300));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(null);
    }
  };

  const handleQuery = async () => {
    const topicSeed = topic.trim() || documentText.trim().slice(0, 300);
    if (!topicSeed) {
      setError("Provide a topic or upload a document first.");
      return;
    }
    setError(null);
    setLoading("Running query agent...");
    try {
      const result = await api.query({
        text: topicSeed,
        top_keywords: topKeywords,
      });
      setQueryResult(result);
      if (!topic.trim()) {
        setTopic(topicSeed);
      }
      setKeywordsInput(result.keywords.join(", "));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setLoading(null);
    }
  };

  const handleRetrieve = async () => {
    const payloadKeywords =
      keywords.length > 0
        ? keywords
        : extractKeywordsFromText(`${topic} ${documentText}`.trim(), 8);

    if (!payloadKeywords.length) {
      setError("Provide keywords, run query, or upload a document first.");
      return;
    }

    setError(null);
    setLoading("Running retrieval agent...");
    try {
      const result = await api.retrieve({
        keywords: payloadKeywords,
        max_results: maxPapers,
        use_multi_query: true,
        subtopics: queryResult?.subtopics,
        sources: retrieveSources,
      });
      setPapers(result);
      setPapersInput(pretty(result));
      if (!keywordsInput.trim()) {
        setKeywordsInput(payloadKeywords.join(", "));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Retrieval failed");
    } finally {
      setLoading(null);
    }
  };

  const handleSummarize = async () => {
    const parsedPapers = papersInput.trim()
      ? parseJson<Paper[]>(papersInput)
      : null;
    if (papersInput.trim() && !parsedPapers) return;

    let payloadPapers = parsedPapers ?? papers;
    if (!payloadPapers.length && documentText.trim()) {
      payloadPapers = textToPaperSeed(documentText);
      if (!papersInput.trim()) {
        setPapersInput(pretty(payloadPapers));
      }
    }

    if (!payloadPapers.length) {
      setError(
        "Provide papers JSON, retrieve papers, or upload a document first.",
      );
      return;
    }

    const payloadKeywords =
      keywords.length > 0
        ? keywords
        : extractKeywordsFromText(`${topic} ${documentText}`.trim(), 8);

    setError(null);
    setLoading("Running summarization agent...");
    try {
      const result = await api.summarize({
        papers: payloadPapers,
        keywords: payloadKeywords,
      });
      setSummary(result);
      setSummaryInput(pretty(result));
      if (!keywordsInput.trim() && payloadKeywords.length) {
        setKeywordsInput(payloadKeywords.join(", "));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Summarization failed");
    } finally {
      setLoading(null);
    }
  };

  const handleDraft = async () => {
    setError(null);
    setLoading("Running drafting agent...");

    const parsedSummary = summaryInput.trim()
      ? parseJson<ComprehensiveSummary>(summaryInput)
      : null;
    if (summaryInput.trim() && !parsedSummary) {
      setLoading(null);
      return;
    }

    const payloadKeywords =
      keywords.length > 0
        ? keywords
        : extractKeywordsFromText(`${topic} ${documentText}`.trim(), 8);

    let payloadSummary = parsedSummary ?? summary;
    const draftTopic = topic.trim() || documentText.trim().slice(0, 300);

    try {
      if (!payloadSummary && documentText.trim()) {
        const seededPapers = textToPaperSeed(documentText);
        const seededSummary = await api.summarize({
          papers: seededPapers,
          keywords: payloadKeywords,
        });
        payloadSummary = seededSummary;
        setSummary(seededSummary);
        setSummaryInput(pretty(seededSummary));
        if (!papersInput.trim()) {
          setPapersInput(pretty(seededPapers));
        }
      }

      if (!payloadSummary) {
        setError(
          "Provide summary JSON, run summarization, or upload a document first.",
        );
        return;
      }

      if (!draftTopic) {
        setError("Provide research topic or upload a document first.");
        return;
      }

      if (!payloadKeywords.length) {
        setError("Provide keywords, run query, or upload a document first.");
        return;
      }

      const result = await api.draft({
        research_topic: draftTopic,
        comprehensive_summary: payloadSummary,
        keywords: payloadKeywords,
      });
      setDraft(result);
      setDraftInput(pretty(result));
      if (!topic.trim()) {
        setTopic(draftTopic);
      }
      if (!keywordsInput.trim()) {
        setKeywordsInput(payloadKeywords.join(", "));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Drafting failed");
    } finally {
      setLoading(null);
    }
  };

  const handlePlagiarism = async () => {
    const parsedDraft = draftInput.trim() ? parseJson<Draft>(draftInput) : null;
    const parsedSources = sourcesInput.trim()
      ? parseJson<Paper[]>(sourcesInput)
      : null;

    if (draftInput.trim() && !parsedDraft) return;
    if (sourcesInput.trim() && !parsedSources) return;

    const payloadDraft =
      parsedDraft ??
      draft ??
      (documentText.trim() ? textToDraftSeed(documentText) : null);
    const payloadSources =
      parsedSources ?? (papers.length ? papers : textToPaperSeed(documentText));
    const payloadTopic = topic.trim() || documentText.trim().slice(0, 300);

    if (!payloadDraft) {
      setError(
        "Provide draft JSON, run draft agent, or upload a document first.",
      );
      return;
    }

    if (!payloadSources.length) {
      setError(
        "Provide source papers JSON, retrieve papers, or upload a document first.",
      );
      return;
    }

    if (!payloadTopic) {
      setError("Provide research topic or upload a document first.");
      return;
    }

    setError(null);
    setLoading("Running plagiarism agent...");
    try {
      const result = await api.plagiarism({
        generated_draft: payloadDraft,
        source_papers: payloadSources,
        research_topic: payloadTopic,
      });
      setPlagiarism(result);
      if (!draft && !draftInput.trim()) {
        setDraft(payloadDraft);
        setDraftInput(pretty(payloadDraft));
      }
      if (!papers.length && !sourcesInput.trim()) {
        setPapers(payloadSources);
        setPapersInput(pretty(payloadSources));
      }
      if (!topic.trim()) {
        setTopic(payloadTopic);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Plagiarism check failed");
    } finally {
      setLoading(null);
    }
  };

  const exportJson = (filename: string, value: unknown) => {
    const blob = new Blob([pretty(value)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 px-2 pb-10 md:px-4">
      <PageHeader
        title="Agent Hub"
        subtitle="Use any agent directly. No forced sequence. Upload once and run what you need."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone={error ? "danger" : loading ? "warning" : "success"}>
              {error ? "Action needed" : (loading ?? "Ready")}
            </Badge>
            <Badge tone="info">Independent mode</Badge>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Keywords"
          value={stats.keywords}
          caption="Active query terms"
        />
        <StatCard
          label="Papers"
          value={stats.papers}
          caption="Loaded source papers"
        />
        <StatCard
          label="Summary"
          value={stats.summarySections}
          caption="Section blocks"
        />
        <StatCard
          label="Plagiarism"
          value={stats.plagiarism}
          caption="Latest score"
        />
      </section>

      <SectionCard
        title="Quick start"
        description="1) Upload document 2) choose an agent below 3) run only that agent"
      >
        <div className="grid gap-3 md:grid-cols-3">
          <button
            onClick={handleSummarize}
            disabled={!documentText.trim() || !!loading}
            className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-3 text-left text-sm text-cyan-200 hover:bg-cyan-500/20 disabled:opacity-50"
          >
            <div className="font-semibold">Summarize document</div>
            <div className="mt-1 text-xs text-cyan-300/80">
              No query/retrieval required
            </div>
          </button>
          <button
            onClick={handleDraft}
            disabled={!documentText.trim() || !!loading}
            className="rounded-xl border border-fuchsia-500/40 bg-fuchsia-500/10 px-4 py-3 text-left text-sm text-fuchsia-200 hover:bg-fuchsia-500/20 disabled:opacity-50"
          >
            <div className="font-semibold">Draft from document</div>
            <div className="mt-1 text-xs text-fuchsia-300/80">
              Auto-seeds missing summary
            </div>
          </button>
          <button
            onClick={handlePlagiarism}
            disabled={!documentText.trim() || !!loading}
            className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-left text-sm text-amber-200 hover:bg-amber-500/20 disabled:opacity-50"
          >
            <div className="font-semibold">Plagiarism check</div>
            <div className="mt-1 text-xs text-amber-300/80">
              Auto-seeds draft and sources
            </div>
          </button>
        </div>
      </SectionCard>

      <SectionCard
        title="Focus view"
        description="Show all agents or focus on one agent panel."
      >
        <div className="flex flex-wrap gap-2">
          {(
            [
              ["all", "All"],
              ["query", "Query"],
              ["retrieval", "Retrieval"],
              ["summary", "Summary"],
              ["draft", "Draft"],
              ["plagiarism", "Plagiarism"],
            ] as Array<[AgentView, string]>
          ).map(([view, label]) => (
            <button
              key={view}
              onClick={() => setActiveView(view)}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                activeView === view
                  ? "border-indigo-400 bg-indigo-500/20 text-indigo-200"
                  : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </SectionCard>

      {(activeView === "all" ||
        activeView === "summary" ||
        activeView === "draft" ||
        activeView === "plagiarism" ||
        activeView === "query" ||
        activeView === "retrieval") && (
        <SectionCard
          title="Document input (PDF / DOC / DOCX / TXT)"
          description="Upload once, then run any agent directly."
        >
          <div className="space-y-3">
            <input
              type="file"
              accept=".txt,.pdf,.doc,.docx"
              onChange={(e) =>
                handleUploadDocument(e.target.files?.[0] ?? null)
              }
              className="w-full rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-800 file:px-3 file:py-1.5 file:text-xs file:text-zinc-200"
            />
            <textarea
              value={documentText}
              onChange={(e) => setDocumentText(e.target.value)}
              placeholder="Extracted document text appears here..."
              rows={7}
              className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs"
            />
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setTopic(documentText.slice(0, 300))}
                disabled={!documentText.trim()}
                className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                Use as topic seed
              </button>
              <button
                onClick={() =>
                  setPapersInput(pretty(textToPaperSeed(documentText)))
                }
                disabled={!documentText.trim()}
                className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                Create papers JSON from text
              </button>
              <button
                onClick={() =>
                  setKeywordsInput(
                    extractKeywordsFromText(
                      `${topic} ${documentText}`.trim(),
                      8,
                    ).join(", "),
                  )
                }
                disabled={!documentText.trim()}
                className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
              >
                Generate keywords
              </button>
              <button
                onClick={handleSummarize}
                disabled={!documentText.trim() || !!loading}
                className="rounded-lg bg-cyan-500 px-3 py-1 text-xs font-medium text-white hover:bg-cyan-400 disabled:opacity-50"
              >
                Summarize uploaded document now
              </button>
              <button
                onClick={handleDraft}
                disabled={!documentText.trim() || !!loading}
                className="rounded-lg bg-fuchsia-500 px-3 py-1 text-xs font-medium text-white hover:bg-fuchsia-400 disabled:opacity-50"
              >
                Draft from uploaded document
              </button>
              <button
                onClick={handlePlagiarism}
                disabled={!documentText.trim() || !!loading}
                className="rounded-lg bg-amber-500 px-3 py-1 text-xs font-medium text-white hover:bg-amber-400 disabled:opacity-50"
              >
                Plagiarism check uploaded document
              </button>
            </div>
            {documentWarnings.length > 0 && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
                {documentWarnings.map((warning) => (
                  <div key={warning}>• {warning}</div>
                ))}
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {(activeView === "all" || activeView === "query") && (
        <SectionCard
          title="1) Query Agent"
          description="Input topic and extract keywords/subtopics."
        >
          <div className="space-y-3">
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Research topic"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
            />
            <div className="flex items-center gap-3">
              <label className="text-xs text-zinc-400">Top keywords</label>
              <input
                type="number"
                min={3}
                max={20}
                value={topKeywords}
                onChange={(e) => setTopKeywords(Number(e.target.value))}
                className="w-24 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
              />
              <button
                onClick={handleQuery}
                disabled={(!topic.trim() && !documentText.trim()) || !!loading}
                className="rounded-lg bg-indigo-500 px-4 py-2 text-sm font-medium hover:bg-indigo-400 disabled:opacity-50"
              >
                Run Query
              </button>
            </div>
            {queryResult && (
              <pre className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                {pretty(queryResult)}
              </pre>
            )}
          </div>
        </SectionCard>
      )}

      {(activeView === "all" || activeView === "retrieval") && (
        <SectionCard
          title="2) Retrieval Agent"
          description="Fetch papers from keywords or custom terms."
        >
          <div className="space-y-3">
            <input
              value={keywordsInput}
              onChange={(e) => setKeywordsInput(e.target.value)}
              placeholder="keyword1, keyword2, keyword3"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
            />
            <div className="flex items-center gap-3">
              <label className="text-xs text-zinc-400">Max papers</label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxPapers}
                onChange={(e) => setMaxPapers(Number(e.target.value))}
                className="w-24 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm"
              />
              <button
                onClick={handleRetrieve}
                disabled={
                  (!keywords.length && !documentText.trim()) || !!loading
                }
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium hover:bg-emerald-400 disabled:opacity-50"
              >
                Run Retrieval
              </button>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <div className="mb-2 text-xs text-zinc-400">Sources</div>
              <div className="flex flex-wrap gap-2 text-xs">
                {[
                  ["arxiv", "arXiv"],
                  ["openalex", "OpenAlex"],
                  ["semantic_scholar", "Semantic Scholar"],
                ].map(([key, label]) => {
                  const checked = retrieveSources.includes(key);
                  return (
                    <label
                      key={key}
                      className="inline-flex items-center gap-2 rounded-full border border-zinc-700 px-3 py-1 text-zinc-300"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          setRetrieveSources((prev) => {
                            if (e.target.checked) {
                              return prev.includes(key) ? prev : [...prev, key];
                            }
                            const next = prev.filter((s) => s !== key);
                            return next.length ? next : ["arxiv"];
                          });
                        }}
                      />
                      {label}
                    </label>
                  );
                })}
              </div>
            </div>
            <textarea
              rows={8}
              value={papersInput}
              onChange={(e) => setPapersInput(e.target.value)}
              placeholder="Paper[] JSON (optional manual input)"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 font-mono text-xs"
            />
            <div className="flex gap-2">
              <button
                onClick={() =>
                  papers.length && exportJson("papers.json", papers)
                }
                className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
              >
                Export papers JSON
              </button>
            </div>
          </div>
        </SectionCard>
      )}

      {(activeView === "all" || activeView === "summary") && (
        <SectionCard
          title="3) Summarization Agent"
          description="Summarize provided papers + keywords."
        >
          <div className="space-y-3">
            <button
              onClick={handleSummarize}
              disabled={
                (!papers.length &&
                  !papersInput.trim() &&
                  !documentText.trim()) ||
                !!loading
              }
              className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium hover:bg-cyan-400 disabled:opacity-50"
            >
              Run Summarization
            </button>
            <textarea
              rows={8}
              value={summaryInput}
              onChange={(e) => setSummaryInput(e.target.value)}
              placeholder="ComprehensiveSummary JSON"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 font-mono text-xs"
            />
            <button
              onClick={() => summary && exportJson("summary.json", summary)}
              className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Export summary JSON
            </button>
            {summary && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                <div className="mb-2 text-zinc-400">Summary preview</div>
                <div className="max-h-52 overflow-auto whitespace-pre-wrap">
                  {String(summary.executive_summary ?? "Summary generated")}
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {(activeView === "all" || activeView === "draft") && (
        <SectionCard
          title="4) Draft Agent"
          description="Generate abstract/introduction/related work."
        >
          <div className="space-y-3">
            <button
              onClick={handleDraft}
              disabled={
                (!summary && !summaryInput.trim() && !documentText.trim()) ||
                (!topic.trim() && !documentText.trim()) ||
                !!loading
              }
              className="rounded-lg bg-fuchsia-500 px-4 py-2 text-sm font-medium hover:bg-fuchsia-400 disabled:opacity-50"
            >
              Run Draft
            </button>
            <textarea
              rows={8}
              value={draftInput}
              onChange={(e) => setDraftInput(e.target.value)}
              placeholder="Draft JSON"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 font-mono text-xs"
            />
            <button
              onClick={() => draft && exportJson("draft.json", draft)}
              className="rounded-lg border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:bg-zinc-800"
            >
              Export draft JSON
            </button>
            {draft && (
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                <div className="mb-2 text-zinc-400">
                  Draft preview (Abstract)
                </div>
                <div className="max-h-40 overflow-auto whitespace-pre-wrap">
                  {draft.abstract}
                </div>
              </div>
            )}
          </div>
        </SectionCard>
      )}

      {(activeView === "all" || activeView === "plagiarism") && (
        <SectionCard
          title="5) Plagiarism Agent"
          description="Check draft against source papers."
        >
          <div className="space-y-3">
            <textarea
              rows={6}
              value={sourcesInput}
              onChange={(e) => setSourcesInput(e.target.value)}
              placeholder="Source Paper[] JSON (optional override)"
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 font-mono text-xs"
            />
            <button
              onClick={handlePlagiarism}
              disabled={
                (!draft && !draftInput.trim() && !documentText.trim()) ||
                (!papers.length &&
                  !sourcesInput.trim() &&
                  !documentText.trim()) ||
                (!topic.trim() && !documentText.trim()) ||
                !!loading
              }
              className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium hover:bg-amber-400 disabled:opacity-50"
            >
              Run Plagiarism
            </button>
            {plagiarism && (
              <pre className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                {pretty(plagiarism)}
              </pre>
            )}
          </div>
        </SectionCard>
      )}

      <SectionCard title="Status">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-sm">
          {error ? (
            <div className="text-rose-400">{error}</div>
          ) : loading ? (
            <div className="text-amber-300">{loading}</div>
          ) : (
            <div className="text-emerald-300">
              All good. Pick any agent and run.
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
