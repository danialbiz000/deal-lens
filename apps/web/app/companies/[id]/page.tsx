"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  type CompanyDetail,
  type ExtractedPeriodCandidate,
  type FinancialPeriod,
  type ManualFinancialPeriodInput,
  type ScreeningScoreResponse,
} from "@/lib/api";
import { DocumentExtractionPanel } from "./DocumentExtractionPanel";
import {
  Badge,
  Button,
  Card,
  CompanySubNav,
  EmptyState,
  Eyebrow,
  Skeleton,
  StatTile,
  colors,
  formatMoney,
  inputStyle,
  scoreTone,
  sourceTone,
  thStyle,
  tdStyle,
  trStyle,
} from "@/lib/ui";

const MANUAL_ENTRY_FIELDS: Array<{ key: keyof ManualFinancialPeriodInput; label: string }> = [
  { key: "revenue", label: "Revenue" },
  { key: "ebitda", label: "EBITDA" },
  { key: "operating_cash_flow", label: "Operating cash flow" },
  { key: "capex", label: "Capex" },
  { key: "total_debt", label: "Total debt" },
  { key: "cash_and_equivalents", label: "Cash & equivalents" },
  { key: "interest_expense", label: "Interest expense" },
];

const PLACEHOLDER_FACTORS = [
  { key: "business_quality_score", label: "Business quality" },
  { key: "market_structure_score", label: "Market structure" },
  { key: "exit_optionality_score", label: "Exit optionality" },
  { key: "management_execution_score", label: "Management / execution" },
];

export default function CompanyDetailPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [financials, setFinancials] = useState<FinancialPeriod[]>([]);
  const [screening, setScreening] = useState<ScreeningScoreResponse | null>(null);
  const [screeningError, setScreeningError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [assumptionDrafts, setAssumptionDrafts] = useState<Record<string, string>>({});
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualDraft, setManualDraft] = useState<Record<string, string>>({
    fiscal_year: String(new Date().getFullYear() - 1),
    period_end_date: `${new Date().getFullYear() - 1}-12-31`,
    period_type: "FY",
    currency: "USD",
  });
  const [manualError, setManualError] = useState<string | null>(null);
  const [activeCitations, setActiveCitations] = useState<Record<string, string | null>>({});

  async function refresh() {
    try {
      const [companyResult, financialsResult] = await Promise.all([
        api.getCompany(companyId),
        api.getFinancials(companyId),
      ]);
      setCompany(companyResult);
      setFinancials(financialsResult);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to load company");
      return;
    }

    try {
      setScreening(await api.getScreeningScore(companyId));
      setScreeningError(null);
    } catch (err) {
      setScreening(null);
      setScreeningError(err instanceof ApiError ? err.message : "failed to load screening score");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleIngest() {
    setBusy(true);
    setError(null);
    try {
      await api.ingestFinancials(companyId, 3);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ingest failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAddManualPeriod(e: React.FormEvent) {
    e.preventDefault();
    setManualError(null);
    setBusy(true);
    try {
      const numericFields: Record<string, number> = {};
      for (const { key } of MANUAL_ENTRY_FIELDS) {
        const raw = manualDraft[key];
        if (raw !== undefined && raw !== "") {
          numericFields[key] = Number(raw);
        }
      }
      const payload: ManualFinancialPeriodInput = {
        fiscal_year: Number(manualDraft.fiscal_year),
        period_end_date: manualDraft.period_end_date,
        period_type: manualDraft.period_type || "FY",
        currency: manualDraft.currency || "USD",
        source_ref: manualDraft.source_ref || undefined,
        ...numericFields,
      };
      await api.addManualFinancialPeriod(companyId, payload);
      setManualDraft({
        fiscal_year: String(new Date().getFullYear() - 1),
        period_end_date: `${new Date().getFullYear() - 1}-12-31`,
        period_type: "FY",
        currency: "USD",
      });
      setActiveCitations({});
      await refresh();
    } catch (err) {
      setManualError(err instanceof ApiError ? err.message : "failed to save manual financial period");
    } finally {
      setBusy(false);
    }
  }

  function handleUseExtractedCandidate(candidate: ExtractedPeriodCandidate) {
    const draft: Record<string, string> = {
      fiscal_year: String(candidate.fiscal_year),
      period_end_date: candidate.period_end_date,
      period_type: candidate.period_type,
      currency: candidate.currency,
      source_ref: "extracted from uploaded document -- review before saving",
    };
    for (const { key } of MANUAL_ENTRY_FIELDS) {
      const value = candidate[key as keyof ExtractedPeriodCandidate];
      if (typeof value === "number") draft[key] = String(value);
    }
    setManualDraft(draft);
    setActiveCitations(candidate.citations);
    setManualError(null);
    setShowManualForm(true);
  }

  async function handleSetAssumption(name: string) {
    const raw = assumptionDrafts[name];
    const value = Number(raw);
    if (Number.isNaN(value)) return;
    setBusy(true);
    setError(null);
    try {
      await api.upsertAssumption(companyId, { name, value_numeric: value, source: "manual:analyst" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to save assumption");
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div>
        <Link href="/" style={{ color: colors.textMuted, fontSize: "0.85rem", textDecoration: "none" }}>
          &larr; all companies
        </Link>
        <Badge tone="danger">{error}</Badge>
      </div>
    );
  }
  if (!company) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <Skeleton height="4rem" />
        <Skeleton height="10rem" />
      </div>
    );
  }

  const latest = company.latest_financial_period;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <Link href="/" style={{ color: colors.textMuted, fontSize: "0.85rem", textDecoration: "none" }}>
        &larr; all companies
      </Link>

      <div>
        <Eyebrow>{company.sector || "sector n/a"} &middot; {company.industry || "industry n/a"}</Eyebrow>
        <div style={{ display: "flex", alignItems: "baseline", gap: "0.6rem", flexWrap: "wrap" }}>
          <h1 style={{ margin: 0, fontSize: "1.6rem" }}>{company.name}</h1>
          <span style={{ color: colors.textMuted, fontSize: "1rem" }}>{company.ticker}</span>
        </div>
      </div>

      <CompanySubNav companyId={companyId} active="overview" />

      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
        <StatTile
          label="PE Screening Score"
          value={screening ? `${screening.score.toFixed(0)} / 100` : "–"}
          tone={screening ? scoreTone(screening.score) : undefined}
        />
        <StatTile label="Revenue (latest FY)" value={latest ? formatMoney(latest.revenue) : "–"} sub={latest ? `FY${latest.fiscal_year}` : undefined} />
        <StatTile label="EBITDA (latest FY)" value={latest ? formatMoney(latest.ebitda) : "–"} sub={latest ? `FY${latest.fiscal_year}` : undefined} />
        <StatTile
          label="Market cap"
          value={company.market_cap !== null ? formatMoney(company.market_cap) : "–"}
          sub={company.market_data_source ? `via ${company.market_data_source}` : undefined}
        />
      </div>

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <div style={{ color: colors.textMuted, fontSize: "0.85rem" }}>
            {company.country || "n/a"} &middot; reports in {company.reporting_currency}
            {!company.cik && (
              <span style={{ display: "block", color: colors.textFaint, marginTop: "0.2rem" }}>
                No CIK on file -- this looks like a private company. SEC EDGAR has no data for it; use
                &quot;Add financials manually&quot; below instead.
              </span>
            )}
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <Button variant="secondary" onClick={() => setShowManualForm((s) => !s)}>
              {showManualForm ? "Hide manual entry" : "Add financials manually"}
            </Button>
            <Button onClick={handleIngest} disabled={busy}>
              {busy ? "Working..." : "Ingest financials (SEC EDGAR + FMP)"}
            </Button>
          </div>
        </div>
      </Card>

      <DocumentExtractionPanel companyId={companyId} onUseCandidate={handleUseExtractedCandidate} />

      {showManualForm && (
        <Card>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Add financials manually</h2>
          <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginTop: 0 }}>
            For a private company with no SEC filing -- these numbers are unaudited and will always be labeled{" "}
            <Badge tone="warning">MANUAL</Badge> everywhere they&apos;re shown, never blended in silently with
            verified filings. Enter whatever you actually have; leave the rest blank.
          </p>
          <form onSubmit={handleAddManualPeriod} style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted }}>
                Fiscal year
                <input
                  type="number"
                  required
                  value={manualDraft.fiscal_year ?? ""}
                  onChange={(e) => setManualDraft((d) => ({ ...d, fiscal_year: e.target.value }))}
                  style={{ ...inputStyle, width: "110px" }}
                />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted }}>
                Period end date
                <input
                  type="date"
                  required
                  value={manualDraft.period_end_date ?? ""}
                  onChange={(e) => setManualDraft((d) => ({ ...d, period_end_date: e.target.value }))}
                  style={{ ...inputStyle, width: "150px" }}
                />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted }}>
                Period type
                <select
                  value={manualDraft.period_type ?? "FY"}
                  onChange={(e) => setManualDraft((d) => ({ ...d, period_type: e.target.value }))}
                  style={{ ...inputStyle, width: "90px" }}
                >
                  {["FY", "Q1", "Q2", "Q3", "Q4", "TTM"].map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted }}>
                Currency
                <input
                  value={manualDraft.currency ?? "USD"}
                  onChange={(e) => setManualDraft((d) => ({ ...d, currency: e.target.value.toUpperCase() }))}
                  maxLength={3}
                  style={{ ...inputStyle, width: "70px" }}
                />
              </label>
              <label style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted, flex: "1 1 220px" }}>
                Source note (optional)
                <input
                  placeholder="e.g. management-provided FY2025 draft P&amp;L"
                  value={manualDraft.source_ref ?? ""}
                  onChange={(e) => setManualDraft((d) => ({ ...d, source_ref: e.target.value }))}
                  style={inputStyle}
                />
              </label>
            </div>
            <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
              {MANUAL_ENTRY_FIELDS.map(({ key, label }) => (
                <label key={key} style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.8rem", color: colors.textMuted }}>
                  {label}
                  <input
                    type="number"
                    placeholder="optional"
                    value={manualDraft[key] ?? ""}
                    onChange={(e) => setManualDraft((d) => ({ ...d, [key]: e.target.value }))}
                    style={{ ...inputStyle, width: "150px" }}
                  />
                  {activeCitations[key] && (
                    <span style={{ color: colors.textFaint, fontSize: "0.7rem", maxWidth: "150px" }}>
                      &ldquo;{activeCitations[key]}&rdquo;
                    </span>
                  )}
                </label>
              ))}
            </div>
            {manualError && <Badge tone="danger">{manualError}</Badge>}
            <div>
              <Button type="submit" disabled={busy}>
                {busy ? "Saving..." : "Save manual financial period"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Screening score breakdown</h2>
          {screening && <span style={{ color: colors.textFaint, fontSize: "0.78rem" }}>formula {screening.formula_version}</span>}
        </div>
        {screeningError ? (
          <Badge tone="warning">{screeningError}</Badge>
        ) : screening ? (
          <>
            <table style={{ width: "100%", marginTop: "0.5rem" }}>
              <thead>
                <tr>
                  <th style={thStyle}>Factor</th>
                  <th style={thStyle}>Weight</th>
                  <th style={thStyle}>Score</th>
                  <th style={thStyle}>Source</th>
                  <th style={thStyle}>Notes</th>
                </tr>
              </thead>
              <tbody>
                {screening.factors.map((f) => (
                  <tr key={f.name} style={trStyle}>
                    <td style={tdStyle}>{f.name.replace(/_/g, " ")}</td>
                    <td style={tdStyle}>{(f.weight * 100).toFixed(0)}%</td>
                    <td style={{ ...tdStyle, fontWeight: 600 }}>{f.normalized_score.toFixed(1)}</td>
                    <td style={tdStyle}>
                      <Badge tone={sourceTone(f.source)}>{f.source}</Badge>
                    </td>
                    <td style={{ ...tdStyle, color: colors.textFaint, fontSize: "0.8rem" }}>{f.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {screening.warnings.length > 0 && (
              <ul style={{ color: colors.warning, fontSize: "0.85rem" }}>
                {screening.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
            <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginBottom: 0 }}>
              Honest limitation: 45% of this score&apos;s weight (business quality, market structure, exit
              optionality, management/execution) is manual/placeholder until an analyst supplies an assumption
              below.
            </p>
          </>
        ) : (
          <Skeleton height="8rem" />
        )}
      </Card>

      <Card>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Manual assumptions (placeholder factors)</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {PLACEHOLDER_FACTORS.map(({ key, label }) => (
            <div key={key} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <label style={{ width: "220px", color: colors.textMuted, fontSize: "0.85rem" }}>{label}</label>
              <input
                type="number"
                min={0}
                max={100}
                placeholder="0-100"
                value={assumptionDrafts[key] ?? ""}
                onChange={(e) => setAssumptionDrafts((d) => ({ ...d, [key]: e.target.value }))}
                style={{ ...inputStyle, width: "100px" }}
              />
              <Button size="sm" variant="secondary" onClick={() => handleSetAssumption(key)} disabled={busy}>
                Save
              </Button>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Financial periods</h2>
        {financials.length === 0 ? (
          <EmptyState>No financials ingested yet -- click &quot;Ingest financials&quot; above.</EmptyState>
        ) : (
          <table style={{ width: "100%" }}>
            <thead>
              <tr>
                <th style={thStyle}>FY</th>
                <th style={thStyle}>Type</th>
                <th style={thStyle}>Source</th>
                <th style={thStyle}>Revenue</th>
                <th style={thStyle}>EBITDA</th>
                <th style={thStyle}>OCF</th>
                <th style={thStyle}>Capex</th>
              </tr>
            </thead>
            <tbody>
              {financials.map((p) => (
                <tr key={p.id} style={trStyle}>
                  <td style={tdStyle}>{p.fiscal_year}</td>
                  <td style={tdStyle}>{p.period_type}</td>
                  <td style={tdStyle}>
                    {p.source === "MANUAL" ? (
                      <Badge tone="warning">MANUAL</Badge>
                    ) : (
                      <span style={{ color: colors.textFaint }}>{p.source}</span>
                    )}
                  </td>
                  <td style={tdStyle}>{formatMoney(p.revenue)}</td>
                  <td style={tdStyle}>{formatMoney(p.ebitda)}</td>
                  <td style={tdStyle}>{formatMoney(p.operating_cash_flow)}</td>
                  <td style={tdStyle}>{formatMoney(p.capex)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
