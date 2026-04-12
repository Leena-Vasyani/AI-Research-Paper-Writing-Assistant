export type Paper = {
  title?: string;
  authors?: string[];
  authors_str?: string;
  abstract?: string;
  published?: string;
  pdf_url?: string;
  entry_id?: string;
  categories?: string[];
  primary_category?: string;
  query_used?: string;
  retrieved_at?: string;
  relevance_score?: number;
  [key: string]: unknown;
};

export type QueryResult = {
  original_topic: string;
  keywords: string[];
  subtopics: Record<string, string[]>;
  complexity_analysis: Record<string, unknown>;
};

export type ComprehensiveSummary = {
  executive_summary?: string;
  section_summaries?: Record<string, string>;
  key_insights?: Record<string, string[]>;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
};

export type Draft = {
  abstract: string;
  introduction: string;
  related_work: string;
};

export type PlagiarismReport = {
  overall_score?: number;
  overall_status?: string;
  overall_message?: string;
  [key: string]: unknown;
};

export type DiagramResult = {
  success: boolean;
  mermaid_code: string;
  provider: string;
  diagram_type: string;
  error?: string;
};

export type CitationReport = {
  cited_draft: Record<string, string>;
  citations_added: number;
  plagiarism_citations: number;
  references: Array<Record<string, unknown>>;
  citation_map: Record<string, unknown>;
};
export type PseudocodeResult = {
  success: boolean;
  latex_code: string;
  provider?: string;
  algorithm_name?: string;
  error?: string;
};

export type ExtractTextResult = {
  success: boolean;
  text: string;
  filename: string;
  extension: string;
  warnings: string[];
};

export type AutocompleteResult = {
  suggestions: string[];
  provider: string;
};

export type CitationCandidate = {
  title: string;
  authors: string;
  year: string;
  source: string;
  doi_or_url: string;
  relevance_score: number;
  citation_type: string;
  in_text: string;
  reference: string;
};

export type CitationSuggestResult = {
  success: boolean;
  claim_text: string;
  citation_style: string;
  candidates: CitationCandidate[];
  confidence: number;
  source_count: number;
  notes: string[];
};

export type CitationFormatResult = {
  in_text: string;
  reference: string;
  paper_info: {
    title: string;
    authors: string;
    year: string;
    source: string;
    url: string;
  };
};

// ── GitHub-to-IEEE ────────────────────────────────────────────────────

export type GitHubToIEEEResult = {
  success: boolean;
  sections: Record<string, string>;
  pdf_base64: string;
  repo_name: string;
  analysis: Record<string, unknown>;
  error?: string;
};

// ── RAG Document Chat ─────────────────────────────────────────────────

export type RAGSession = {
  id: string;
  name: string;
  created_at: string;
  last_active: string;
  document_count: number;
};

export type RAGSessionCreateResult = {
  session_id: string;
  name: string;
  created_at: string;
};

export type RAGMessage = {
  role: "user" | "assistant";
  content: string;
  sources: RAGSource[];
  created_at: string;
};

export type RAGSource = {
  source: string;
  page?: number;
  relevance: number;
  snippet: string;
};

export type RAGQueryResult = {
  answer: string;
  sources: RAGSource[];
};

export type RAGUploadResult = {
  success: boolean;
  processed: number;
  chunks: number;
  errors: string[];
};
