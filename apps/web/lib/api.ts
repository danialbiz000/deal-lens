/**
 * Thin fetch client for apps/api. Deliberately not a heavy SDK -- this
 * slice's contract is small (design doc section 4) and the point is
 * proving the contract end-to-end, not building an abstraction layer.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Company {
  id: string;
  ticker: string;
  cik: string | null;
  name: string;
  sector: string | null;
  industry: string | null;
  country: string | null;
  reporting_currency: string;
  description: string | null;
  market_cap: number | null;
  share_price: number | null;
  market_data_as_of: string | null;
  market_data_source: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialPeriod {
  id: string;
  company_id: string;
  fiscal_year: number;
  period_end_date: string;
  period_type: string;
  currency: string;
  source: string;
  source_ref: string | null;
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
  is_estimate: boolean;
  ingested_at: string;
}

export interface CompanyDetail extends Company {
  latest_financial_period: FinancialPeriod | null;
}

export interface ManualFinancialPeriodInput {
  fiscal_year: number;
  period_end_date: string; // YYYY-MM-DD
  period_type?: string;
  currency?: string;
  source_ref?: string;
  revenue?: number;
  gross_profit?: number;
  ebitda?: number;
  ebit?: number;
  net_income?: number;
  operating_cash_flow?: number;
  capex?: number;
  total_debt?: number;
  cash_and_equivalents?: number;
  interest_expense?: number;
  shares_outstanding?: number;
}

export interface ScreeningFactor {
  name: string;
  weight: number;
  normalized_score: number;
  source: "computed" | "default" | "assumption";
  contribution: number;
  notes: string;
}

export interface ScreeningScoreResponse {
  company_id: string;
  formula_version: string;
  score: number;
  factors: ScreeningFactor[];
  warnings: string[];
  computed_at: string;
}

export interface Assumption {
  id: string;
  company_id: string;
  name: string;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  source: string;
  confidence: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface IngestResponse {
  company_id: string;
  ingested_periods: number;
  periods: FinancialPeriod[];
  warnings: string[];
}

// --- Phase 2: comps / valuation / scenarios / LBO ---

export interface Peer {
  id: string;
  target_company_id: string;
  peer_company_id: string;
  peer_ticker: string | null;
  peer_name: string | null;
  status: "CANDIDATE" | "SELECTED" | "REJECTED";
  reason_code: string | null;
  reason_notes: string | null;
  similarity_score: number | null;
  ev_revenue_multiple: number | null;
  ev_ebitda_multiple: number | null;
  source: string;
  computed_at: string;
  created_at: string;
  updated_at: string;
}

export interface PeerGenerateResponse {
  target_company_id: string;
  peers: Peer[];
  selected_count: number;
  warnings: string[];
}

export interface ValuationResponse {
  company_id: string;
  peer_count: number;
  median_ev_revenue: number;
  q1_ev_revenue: number;
  q3_ev_revenue: number;
  median_ev_ebitda: number;
  q1_ev_ebitda: number;
  q3_ev_ebitda: number;
  implied_ev_from_revenue: number;
  implied_ev_from_ebitda: number;
  entry_ev: number;
  entry_net_debt: number;
  entry_equity_value: number;
  computed_at: string;
}

export type CaseType = "base" | "bull" | "bear";

export interface Scenario {
  id: string;
  company_id: string;
  case_type: "BASE" | "BULL" | "BEAR";
  revenue_growth_rate: number;
  ebitda_margin_delta: number;
  exit_multiple_delta: number;
  source: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScenarioGenerateResponse {
  company_id: string;
  scenarios: Scenario[];
  warnings: string[];
}

export interface TrancheYear {
  name: string;
  beginning_balance: number;
  ending_balance: number;
  interest: number | null;
  mandatory_amort: number | null;
  sweep: number | null;
}

export interface ScheduleYear {
  year: number;
  revenue: number;
  ebitda: number;
  beginning_debt: number;
  ending_debt: number;
  beginning_cash: number;
  ending_cash: number;
  margin: number | null;
  capex: number | null;
  nwc_investment: number | null;
  interest: number | null;
  taxes: number | null;
  cfads: number | null;
  mandatory_amort: number | null;
  sweep: number | null;
  tranches: TrancheYear[] | null;
}

export interface DebtTrancheInput {
  name: string;
  leverage_multiple: number;
  interest_rate: number;
  mandatory_amort_pct?: number;
  priority?: number;
}

export interface ValueCreationBridge {
  entry_equity: number;
  ebitda_growth: number;
  margin_expansion: number;
  debt_paydown: number;
  multiple_expansion: number;
  transaction_fees: number;
  total: number;
  exit_multiple_dependent: boolean;
  value_destructive: boolean;
}

export interface LboCaseResponse {
  company_id: string;
  scenario_id: string;
  case_type: string;
  formula_version: string;
  inputs: Record<string, number>;
  sources_uses: { new_debt: number; sponsor_equity: number; purchase_ev: number; fees: number; reconciles: boolean };
  schedule: ScheduleYear[];
  entry_ev: number;
  exit_ev: number;
  exit_equity_value: number;
  moic: number;
  irr: number;
  entry_leverage: number;
  exit_leverage: number;
  entry_multiple: number;
  exit_multiple: number;
  value_creation_bridge: ValueCreationBridge;
  warnings: string[];
  computed_at: string;
}

export interface SensitivityResponse {
  company_id: string;
  case_type: string;
  entry_multiples: number[];
  exit_multiples: number[];
  irr_grid: number[][];
  moic_grid: number[][];
}

export interface TornadoVariable {
  variable: string;
  label: string;
  base_value: number;
  low_value: number;
  high_value: number;
  base_irr: number;
  low_irr: number;
  high_irr: number;
  base_moic: number;
  low_moic: number;
  high_moic: number;
  spread: number;
}

export interface TornadoResponse {
  company_id: string;
  case_type: string;
  variables: TornadoVariable[];
}

// --- Phase 4: AI layer (memo writer + IC simulator) ---

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

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // ignore -- fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listCompanies: () => request<Company[]>("/companies"),

  getCompany: (id: string) => request<CompanyDetail>(`/companies/${id}`),

  createCompany: (payload: {
    ticker: string;
    name: string;
    cik?: string;
    sector?: string;
    industry?: string;
    country?: string;
    reporting_currency?: string;
  }) => request<Company>("/companies", { method: "POST", body: JSON.stringify(payload) }),

  getFinancials: (id: string, params?: { period_type?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.period_type) query.set("period_type", params.period_type);
    if (params?.limit) query.set("limit", String(params.limit));
    const qs = query.toString();
    return request<FinancialPeriod[]>(`/companies/${id}/financials${qs ? `?${qs}` : ""}`);
  },

  ingestFinancials: (id: string, years_back = 3) =>
    request<IngestResponse>(`/companies/${id}/ingest`, {
      method: "POST",
      body: JSON.stringify({ years_back }),
    }),

  addManualFinancialPeriod: (id: string, payload: ManualFinancialPeriodInput) =>
    request<FinancialPeriod>(`/companies/${id}/financials`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getScreeningScore: (id: string) => request<ScreeningScoreResponse>(`/companies/${id}/screening-score`),

  listAssumptions: (id: string) => request<Assumption[]>(`/companies/${id}/assumptions`),

  upsertAssumption: (
    id: string,
    payload: { name: string; value_numeric: number; source: string; unit?: string; notes?: string }
  ) =>
    request<Assumption>(`/companies/${id}/assumptions`, {
      method: "POST",
      body: JSON.stringify({ unit: "score_0_100", ...payload }),
    }),

  // --- Phase 2 ---

  generatePeers: (id: string) => request<PeerGenerateResponse>(`/companies/${id}/peers/generate`, { method: "POST" }),

  listPeers: (id: string, status?: string) => {
    const qs = status ? `?status=${status}` : "";
    return request<Peer[]>(`/companies/${id}/peers${qs}`);
  },

  patchPeer: (companyId: string, peerId: string, payload: { status: string; reason_notes: string }) =>
    request<Peer>(`/companies/${companyId}/peers/${peerId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  getValuation: (id: string) => request<ValuationResponse>(`/companies/${id}/valuation`),

  generateScenarios: (id: string) =>
    request<ScenarioGenerateResponse>(`/companies/${id}/scenarios/generate`, { method: "POST" }),

  patchScenario: (
    id: string,
    caseType: CaseType,
    payload: Partial<{ revenue_growth_rate: number; ebitda_margin_delta: number; exit_multiple_delta: number; notes: string }>
  ) =>
    request<Scenario>(`/companies/${id}/scenarios/${caseType}`, { method: "PATCH", body: JSON.stringify(payload) }),

  runLbo: (id: string, caseType: CaseType, entryEv?: number, debtTranches?: DebtTrancheInput[]) =>
    request<LboCaseResponse>(`/companies/${id}/lbo/${caseType}/run`, {
      method: "POST",
      body: JSON.stringify({
        ...(entryEv !== undefined ? { entry_ev: entryEv } : {}),
        ...(debtTranches !== undefined ? { debt_tranches: debtTranches } : {}),
      }),
    }),

  getLbo: (id: string, caseType: CaseType) => request<LboCaseResponse>(`/companies/${id}/lbo/${caseType}`),

  getLboSensitivity: (id: string, caseType: CaseType, step = 1.0, size = 4) =>
    request<SensitivityResponse>(`/companies/${id}/lbo/${caseType}/sensitivity?step=${step}&size=${size}`),

  getLboTornado: (id: string, caseType: CaseType) =>
    request<TornadoResponse>(`/companies/${id}/lbo/${caseType}/tornado`),

  // --- Phase 4 ---

  generateMemo: (id: string) => request<MemoResponse>(`/companies/${id}/memo`, { method: "POST" }),

  listMemos: (id: string) => request<MemoSummary[]>(`/companies/${id}/memo`),

  getMemo: (id: string, version: number) => request<MemoResponse>(`/companies/${id}/memo/${version}`),

  generateIcSimulation: (id: string) =>
    request<IcSimulationResponse>(`/companies/${id}/ic-simulation`, { method: "POST" }),

  listIcSimulations: (id: string) => request<IcSimulationSummary[]>(`/companies/${id}/ic-simulation`),

  getIcSimulation: (id: string, version: number) =>
    request<IcSimulationResponse>(`/companies/${id}/ic-simulation/${version}`),
};

export { ApiError };
