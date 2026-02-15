export type Paper = Record<string, unknown>;

export type QueryResult = {
  original_topic: string;
  keywords: string[];
  subtopics: Record<string, string[]>;
  complexity_analysis: Record<string, unknown>;
};

export type ComprehensiveSummary = {
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
