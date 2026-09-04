/**
 * Phase 4: AI layer (memo writer + IC simulator) + document extraction --
 * split out of lib/api.ts purely to keep that file under this project's
 * 500-line limit. Re-exported from lib/api.ts so existing `from "@/lib/api"`
 * imports elsewhere don't need to change.
 */

import { request, requestForm } from "./api-client";

export interface ExtractedPeriodCandidate {
  fiscal_year: number;
  period_end_date: string;
  period_type: string;
  currency: string;
  revenue: number | null;
  gross_profit: number | null;
  ebitda: number | null;
  ebit: number | null;
  net_income: number | null;
  operating_cash_flow: number | null;
  capex: number | null;
  total_debt: number | null;
  cash_and_equivalents: number | null;
  interest_expense: number | null;
  shares_outstanding: number | null;
  citations: Record<string, string | null>;
}

export interface DocumentExtractionResponse {
  periods: ExtractedPeriodCandidate[];
  notes: string;
}

export interface MemoSection {
  section_key: string;
  title: string;
  content: string;
}

export interface MemoValidationReport {
  total_citations: number;
  invalid_citations: string[];
  mismatched_citations: string[];
  uncited_numbers: string[];
  status: "ok" | "warnings";
  per_section: Array<Record<string, unknown>>;
}

export interface MemoResponse {
  id: string;
  company_id: string;
  version: number;
  prompt_version: string;
  model: string;
  sections: MemoSection[];
  validation_report: MemoValidationReport;
  generated_at: string;
}

export interface MemoSummary {
  id: string;
  version: number;
  generated_at: string;
  validation_status: string;
}

export interface IcRoleOutput {
  role: string;
  output: Record<string, unknown>;
  validation_report: { total_citations: number; invalid_citations: string[]; uncited_numbers: string[]; status: string };
}

export interface IcSimulationResponse {
  id: string;
  company_id: string;
  version: number;
  model: string;
  transcript: IcRoleOutput[];
  llm_recommendation: string;
  recommendation: string;
  override_fired: boolean;
  override_reason: string | null;
  key_strengths: string[];
  key_risks: string[];
  unanswered_dd: string[];
  generated_at: string;
}

export interface IcSimulationSummary {
  id: string;
  version: number;
  generated_at: string;
  recommendation: string;
  override_fired: boolean;
}

export const aiApi = {
  extractFinancialsFromDocument: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return requestForm<DocumentExtractionResponse>(`/companies/${id}/documents/extract`, formData);
  },

  generateMemo: (id: string) => request<MemoResponse>(`/companies/${id}/memo`, { method: "POST" }),

  listMemos: (id: string) => request<MemoSummary[]>(`/companies/${id}/memo`),

  getMemo: (id: string, version: number) => request<MemoResponse>(`/companies/${id}/memo/${version}`),

  generateIcSimulation: (id: string) =>
    request<IcSimulationResponse>(`/companies/${id}/ic-simulation`, { method: "POST" }),

  listIcSimulations: (id: string) => request<IcSimulationSummary[]>(`/companies/${id}/ic-simulation`),

  getIcSimulation: (id: string, version: number) =>
    request<IcSimulationResponse>(`/companies/${id}/ic-simulation/${version}`),
};
