export interface DocumentItem {
  id: number;
  company: string;
  fiscal_year: number;
  form_type: string;
  fiscal_year_end?: string | null;
  filename: string;
  storage_path?: string | null;
  content_hash: string;
  upload_date: string;
}

export interface DocumentUploadResult {
  document: DocumentItem;
  is_duplicate: boolean;
  message: string;
}

export interface RawMetric {
  id: number;
  document_id: number;
  metric_name: string;
  value: number | string;
  unit: string;
  currency: string;
  source_page: number;
  source_chunk_id?: string | null;
  verified: boolean;
  low_confidence: boolean;
}

export interface CalculatedRatios {
  gross_margin_pct?: number | string | null;
  operating_margin_pct?: number | string | null;
  net_margin_pct?: number | string | null;
  free_cash_flow?: number | string | null;
  debt_to_equity?: number | string | null;
  return_on_equity_pct?: number | string | null;
  return_on_assets_pct?: number | string | null;
}

export interface CompanyFinancialSummary {
  document_id: number;
  company: string;
  fiscal_year: number;
  raw_metrics: Record<string, RawMetric>;
  ratios: CalculatedRatios;
  yoy_growth: Record<string, number | null>;
}

export interface CitationItem {
  chunk_id: string;
  page_number: number;
  section_path?: string | null;
  element_type?: string | null;
  snippet?: string | null;
}

export interface ChatResponse {
  answer: string;
  query_type: "STRUCTURED" | "NARRATIVE" | "HYBRID" | string;
  citations: CitationItem[];
  retrieved_chunk_ids: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  query_type?: string;
  citations?: CitationItem[];
  timestamp: string;
}
