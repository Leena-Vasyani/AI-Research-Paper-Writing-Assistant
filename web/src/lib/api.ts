import type {
  ComprehensiveSummary,
  Draft,
  Paper,
  PlagiarismReport,
  PseudocodeResult,
  QueryResult,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function normalizePath(base: string, path: string): string {
  const trimmedBase = base.replace(/\/+$/, "");
  if (trimmedBase.endsWith("/api") && path.startsWith("/api")) {
    return `${trimmedBase}${path.replace(/^\/api/, "")}`;
  }
  return `${trimmedBase}${path}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(normalizePath(API_BASE, path), {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  query: (payload: { text: string; top_keywords: number }) =>
    request<QueryResult>("/api/query", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  retrieve: (payload: {
    keywords: string[];
    max_results: number;
    use_multi_query: boolean;
    subtopics?: Record<string, string[]>;
  }) =>
    request<Paper[]>("/api/retrieve", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  summarize: (payload: { papers: Paper[]; keywords: string[] }) =>
    request<ComprehensiveSummary>("/api/summarize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  draft: (payload: {
    research_topic: string;
    comprehensive_summary: ComprehensiveSummary;
    keywords: string[];
    config?: Record<string, unknown>;
  }) =>
    request<Draft>("/api/draft", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  plagiarism: (payload: {
    generated_draft: Record<string, string>;
    source_papers: Paper[];
    research_topic: string;
  }) =>
    request<PlagiarismReport>("/api/plagiarism", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  refineBlock: (payload: {
    text: string;
    mode: "expand" | "academic" | "refine";
  }) =>
    request<{ refined_text: string; provider: string }>("/api/refine-block", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  generateDiagram: (payload: { description: string; diagram_type?: string }) =>
    request<{
      success: boolean;
      mermaid_code: string;
      provider: string;
      diagram_type: string;
      error?: string;
    }>("/api/diagram", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  convertToPseudocode: (payload: { code: string; algorithm_name?: string }) =>
    request<PseudocodeResult>("/api/pseudocode", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  formatCommands: (payload: {
    prompt: string;
    settings: Record<string, unknown>;
    available_targets: string[];
  }) =>
    request<{
      cssUpdates: Record<string, unknown>;
      editorCommands: { target: string; action: string }[];
      provider: string;
    }>("/api/format-commands", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // IEEE Paper Formatting
  formatIEEE: (payload: {
    raw_text: string;
    format_type: "conference" | "journal" | "transactions";
    detect_equations?: boolean;
    detect_references?: boolean;
  }) =>
    request<{
      success: boolean;
      formatted_html: string;
      sections_detected: number;
      equations_found: number;
      references_found: number;
      provider: string;
      error?: string;
    }>("/api/format-ieee", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // PDF Compilation
  compilePDF: (payload: { latex_code: string }) =>
    request<{
      success: boolean;
      pdf_base64?: string;
      error?: string;
      compilation_log?: string;
    }>("/api/compile-pdf", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
