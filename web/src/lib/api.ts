import type {
  ComprehensiveSummary,
  Draft,
  Paper,
  PlagiarismReport,
  QueryResult,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
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
};
