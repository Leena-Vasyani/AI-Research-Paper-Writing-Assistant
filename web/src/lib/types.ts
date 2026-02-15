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
