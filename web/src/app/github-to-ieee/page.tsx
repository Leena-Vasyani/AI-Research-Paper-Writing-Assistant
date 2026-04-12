"use client";

import { useState } from "react";
import PageHeader from "@/components/PageHeader";
import Badge from "@/components/Badge";
import { api } from "@/lib/api";
import type { GitHubToIEEEResult } from "@/lib/types";

type ProgressStep =
  | "idle"
  | "fetching"
  | "analyzing"
  | "generating"
  | "building"
  | "done"
  | "error";

const stepLabels: Record<ProgressStep, string> = {
  idle: "Ready",
  fetching: "Fetching repository data…",
  analyzing: "Analyzing codebase…",
  generating: "Generating IEEE paper sections…",
  building: "Building PDF…",
  done: "Paper generated successfully!",
  error: "Generation failed",
};

export default function GitHubToIEEEPage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [author, setAuthor] = useState("");
  const [institution, setInstitution] = useState("");
  const [maxFiles, setMaxFiles] = useState(40);
  const [progress, setProgress] = useState<ProgressStep>("idle");
  const [result, setResult] = useState<GitHubToIEEEResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(
    "abstract",
  );

  const handleGenerate = async () => {
    if (!repoUrl.trim()) {
      setError("Please enter a GitHub repository URL.");
      return;
    }

    setError(null);
    setResult(null);
    setProgress("fetching");

    try {
      // Simulate step progression visually
      const timer1 = setTimeout(() => setProgress("analyzing"), 4000);
      const timer2 = setTimeout(() => setProgress("generating"), 8000);
      const timer3 = setTimeout(() => setProgress("building"), 18000);

      const res = await api.githubToIEEE({
        repo_url: repoUrl.trim(),
        author: author.trim(),
        institution: institution.trim(),
        max_files: maxFiles,
      });

      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);

      if (!res.success) {
        setError(res.error || "Failed to generate paper.");
        setProgress("error");
        return;
      }

      setResult(res);
      setProgress("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error occurred.");
      setProgress("error");
    }
  };

  const handleDownloadPDF = () => {
    if (!result?.pdf_base64) return;
    const binary = atob(result.pdf_base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.repo_name || "paper"}_ieee_paper.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isLoading =
    progress !== "idle" && progress !== "done" && progress !== "error";

  const progressPercent: Record<ProgressStep, number> = {
    idle: 0,
    fetching: 15,
    analyzing: 35,
    generating: 65,
    building: 90,
    done: 100,
    error: 0,
  };

  return (
    <div className="space-y-6 px-2 md:px-4">
      <PageHeader
        title="GitHub → IEEE Paper"
        subtitle="Transform any GitHub repository into a structured IEEE-format research paper with one click."
      />

      {/* ── Input Form ───────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-6 backdrop-blur-sm">
        <div className="space-y-5">
          {/* Repo URL */}
          <div>
            <label
              htmlFor="github-to-ieee-repo-url"
              className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-zinc-500"
            >
              GitHub Repository URL
            </label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600">
                <svg
                  className="h-4 w-4"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                </svg>
              </span>
              <input
                id="github-to-ieee-repo-url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                disabled={isLoading}
                className="w-full rounded-xl border border-zinc-700/60 bg-zinc-950 py-3 pl-10 pr-4 text-[13px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          {/* Author + Institution */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label
                htmlFor="github-to-ieee-author"
                className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-zinc-500"
              >
                Author Name
              </label>
              <input
                id="github-to-ieee-author"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="John Doe"
                disabled={isLoading}
                className="w-full rounded-xl border border-zinc-700/60 bg-zinc-950 px-4 py-2.5 text-[13px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors disabled:opacity-50"
              />
            </div>
            <div>
              <label
                htmlFor="github-to-ieee-institution"
                className="mb-1.5 block text-[11px] font-semibold uppercase tracking-widest text-zinc-500"
              >
                Institution
              </label>
              <input
                id="github-to-ieee-institution"
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="University of Example"
                disabled={isLoading}
                className="w-full rounded-xl border border-zinc-700/60 bg-zinc-950 px-4 py-2.5 text-[13px] font-medium text-zinc-200 placeholder:text-zinc-600 focus:border-indigo-500/60 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-colors disabled:opacity-50"
              />
            </div>
          </div>

          {/* Max files slider */}
          <div>
            <label className="mb-1.5 flex items-center justify-between text-[11px] font-semibold uppercase tracking-widest text-zinc-500">
              <span>Max files to analyze</span>
              <span className="text-indigo-300">{maxFiles}</span>
            </label>
            <input
              type="range"
              min={5}
              max={80}
              value={maxFiles}
              onChange={(e) => setMaxFiles(Number(e.target.value))}
              disabled={isLoading}
              className="w-full accent-indigo-500 disabled:opacity-50"
            />
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={!repoUrl.trim() || isLoading}
            className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3 text-[14px] font-semibold tracking-wide text-white shadow-lg shadow-indigo-500/20 transition-all hover:from-indigo-500 hover:to-violet-500 hover:shadow-indigo-500/30 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {isLoading ? "Generating…" : "Generate IEEE Paper"}
          </button>
        </div>
      </div>

      {/* ── Progress Bar ─────────────────────────────────────────────── */}
      {progress !== "idle" && (
        <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-[13px] font-medium text-zinc-300">
              {stepLabels[progress]}
            </span>
            <Badge
              tone={
                progress === "done"
                  ? "success"
                  : progress === "error"
                    ? "danger"
                    : "warning"
              }
            >
              {progress === "done"
                ? "Complete"
                : progress === "error"
                  ? "Error"
                  : "Processing"}
            </Badge>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${
                progress === "error"
                  ? "bg-red-500"
                  : progress === "done"
                    ? "bg-emerald-500"
                    : "bg-indigo-500"
              }`}
              style={{ width: `${progressPercent[progress]}%` }}
            />
          </div>

          {/* Step indicators */}
          <div className="mt-4 grid grid-cols-4 gap-2">
            {(
              ["fetching", "analyzing", "generating", "building"] as const
            ).map((step) => {
              const stepIdx = [
                "fetching",
                "analyzing",
                "generating",
                "building",
              ].indexOf(step);
              const currentIdx = [
                "fetching",
                "analyzing",
                "generating",
                "building",
              ].indexOf(progress);
              const isDone = progress === "done" || currentIdx > stepIdx;
              const isActive = progress === step;

              return (
                <div
                  key={step}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-[11px] font-medium transition-colors ${
                    isDone
                      ? "border-emerald-800/40 bg-emerald-950/30 text-emerald-300"
                      : isActive
                        ? "border-indigo-700/40 bg-indigo-950/40 text-indigo-300"
                        : "border-zinc-800/60 text-zinc-600"
                  }`}
                >
                  <span
                    className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] ${
                      isDone
                        ? "bg-emerald-500 text-white"
                        : isActive
                          ? "bg-indigo-500 text-white"
                          : "bg-zinc-800 text-zinc-500"
                    }`}
                  >
                    {isDone ? "✓" : stepIdx + 1}
                  </span>
                  <span className="capitalize">{step}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Error ────────────────────────────────────────────────────── */}
      {error && (
        <div className="rounded-2xl border border-red-800/40 bg-red-950/30 p-4 text-[13px] text-red-300">
          <span className="font-semibold">Error: </span>
          {error}
        </div>
      )}

      {/* ── Result ───────────────────────────────────────────────────── */}
      {result && result.success && (
        <div className="space-y-4">
          {/* Title + download */}
          <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-6 backdrop-blur-sm">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex-1">
                <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-1">
                  Generated Title
                </div>
                <h2 className="text-xl font-semibold tracking-tight text-zinc-100">
                  {result.sections.title || "Untitled Paper"}
                </h2>
                {author && (
                  <p className="mt-1 text-[13px] text-zinc-400">{author}</p>
                )}
                {institution && (
                  <p className="text-[12px] italic text-zinc-500">
                    {institution}
                  </p>
                )}
              </div>
              <button
                onClick={handleDownloadPDF}
                className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-[13px] font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-500 hover:shadow-emerald-500/30"
              >
                <svg
                  className="h-4 w-4"
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
                Download PDF
              </button>
            </div>
          </div>

          {/* Paper sections */}
          <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-6 backdrop-blur-sm">
            <h3 className="text-[14px] font-semibold tracking-wide text-zinc-100 mb-4">
              Paper Sections
            </h3>
            <div className="space-y-2">
              {[
                { key: "abstract", label: "Abstract" },
                { key: "introduction", label: "I. Introduction" },
                { key: "methodology", label: "II. Methodology" },
                { key: "implementation", label: "III. Implementation" },
                { key: "results", label: "IV. Results and Evaluation" },
                { key: "conclusion", label: "V. Conclusion" },
                { key: "references", label: "References" },
              ].map(({ key, label }) => {
                const content = result.sections[key];
                if (!content) return null;
                const isExpanded = expandedSection === key;
                return (
                  <div
                    key={key}
                    className="rounded-xl border border-zinc-800/50 bg-zinc-950/60"
                  >
                    <button
                      onClick={() =>
                        setExpandedSection(isExpanded ? null : key)
                      }
                      className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-zinc-800/30"
                    >
                      <span className="text-[13px] font-semibold text-zinc-200">
                        {label}
                      </span>
                      <svg
                        className={`h-4 w-4 text-zinc-500 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </button>
                    {isExpanded && (
                      <div className="border-t border-zinc-800/50 px-4 py-3">
                        <p className="whitespace-pre-line text-[12.5px] leading-[1.75] text-zinc-300">
                          {content}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Analysis metadata */}
          {result.analysis &&
            Object.keys(result.analysis).length > 0 && (
              <div className="rounded-2xl border border-zinc-800/70 bg-zinc-900/60 p-6 backdrop-blur-sm">
                <h3 className="text-[14px] font-semibold tracking-wide text-zinc-100 mb-4">
                  Repository Analysis
                </h3>
                <div className="grid gap-3 md:grid-cols-2">
                  {Object.entries(result.analysis).map(([key, value]) => (
                    <div
                      key={key}
                      className="rounded-lg border border-zinc-800/50 bg-zinc-950/50 p-3"
                    >
                      <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
                        {key.replace(/_/g, " ")}
                      </div>
                      <div className="mt-1 text-[12px] leading-relaxed text-zinc-300">
                        {Array.isArray(value)
                          ? (value as string[]).join(", ")
                          : String(value || "—")}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
        </div>
      )}
    </div>
  );
}
