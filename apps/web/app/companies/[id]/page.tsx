"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  api,
  ApiError,
  type CompanyDetail,
  type FinancialPeriod,
  type ScreeningScoreResponse,
} from "@/lib/api";

const cardStyle: React.CSSProperties = {
  border: "1px solid #1f2430",
  borderRadius: "8px",
  padding: "1rem",
  background: "#11151d",
};

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
      setScreeningError(
        err instanceof ApiError ? err.message : "failed to load screening score"
      );
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
    return <p style={{ color: "#ff6b6b" }}>{error}</p>;
  }
  if (!company) {
    return <p>Loading...</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <section style={cardStyle}>
        <h1 style={{ marginTop: 0 }}>
          {company.name} <span style={{ color: "#7c8494" }}>({company.ticker})</span>
        </h1>
        <p style={{ color: "#7c8494" }}>
          {company.sector || "n/a"} &middot; {company.industry || "n/a"} &middot;{" "}
          {company.country || "n/a"} &middot; reports in {company.reporting_currency}
        </p>
        <button onClick={handleIngest} disabled={busy} style={buttonStyle}>
          {busy ? "Working..." : "Ingest financials (SEC EDGAR + FMP)"}
        </button>
        {company.market_cap !== null && (
          <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
            Market cap: {company.market_cap.toLocaleString(undefined, { maximumFractionDigits: 0 })}{" "}
            (as of {company.market_data_as_of}, via {company.market_data_source})
          </p>
        )}
        <div style={{ display: "flex", gap: "1rem", marginTop: "0.5rem" }}>
          <Link href={`/companies/${companyId}/valuation`} style={{ color: "#4f7cff" }}>
            Valuation &amp; comps &rarr;
          </Link>
          <Link href={`/companies/${companyId}/lbo`} style={{ color: "#4f7cff" }}>
            LBO underwriting &rarr;
          </Link>
          <Link href={`/companies/${companyId}/memo`} style={{ color: "#4f7cff" }}>
            Investment memo &rarr;
          </Link>
          <Link href={`/companies/${companyId}/ic-simulation`} style={{ color: "#4f7cff" }}>
            IC simulation &rarr;
          </Link>
        </div>
      </section>

      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Screening score</h2>
        {screeningError ? (
          <p style={{ color: "#e0a030" }}>{screeningError}</p>
        ) : screening ? (
          <>
            <div style={{ fontSize: "2.5rem", fontWeight: 700 }}>{screening.score} / 100</div>
            <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
              formula {screening.formula_version} &middot; computed {screening.computed_at}
            </p>
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "0.75rem" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#7c8494", fontSize: "0.8rem" }}>
                  <th>Factor</th>
                  <th>Weight</th>
                  <th>Score</th>
                  <th>Source</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {screening.factors.map((f) => (
                  <tr key={f.name} style={{ borderTop: "1px solid #1f2430" }}>
                    <td style={{ padding: "0.4rem 0" }}>{f.name.replace(/_/g, " ")}</td>
                    <td>{(f.weight * 100).toFixed(0)}%</td>
                    <td>{f.normalized_score.toFixed(1)}</td>
                    <td>
                      <span style={sourceTagStyle(f.source)}>{f.source}</span>
                    </td>
                    <td style={{ color: "#7c8494", fontSize: "0.8rem" }}>{f.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {screening.warnings.length > 0 && (
              <ul style={{ color: "#e0a030", fontSize: "0.85rem" }}>
                {screening.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
            <p style={{ color: "#7c8494", fontSize: "0.8rem" }}>
              Honest limitation: 45% of this score&apos;s weight (business quality, market
              structure, exit optionality, management/execution) is manual/placeholder until an
              analyst supplies an assumption below.
            </p>
          </>
        ) : (
          <p>Loading...</p>
        )}
      </section>

      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Manual assumptions (placeholder factors)</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {PLACEHOLDER_FACTORS.map(({ key, label }) => (
            <div key={key} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <label style={{ width: "220px" }}>{label}</label>
              <input
                type="number"
                min={0}
                max={100}
                placeholder="0-100"
                value={assumptionDrafts[key] ?? ""}
                onChange={(e) => setAssumptionDrafts((d) => ({ ...d, [key]: e.target.value }))}
                style={{ ...inputStyle, width: "100px" }}
              />
              <button onClick={() => handleSetAssumption(key)} disabled={busy} style={buttonStyle}>
                Save
              </button>
            </div>
          ))}
        </div>
      </section>

      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Financial periods</h2>
        {financials.length === 0 ? (
          <p style={{ color: "#7c8494" }}>No financials ingested yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "#7c8494" }}>
                <th>FY</th>
                <th>Type</th>
                <th>Source</th>
                <th>Revenue</th>
                <th>EBITDA</th>
                <th>OCF</th>
                <th>Capex</th>
              </tr>
            </thead>
            <tbody>
              {financials.map((p) => (
                <tr key={p.id} style={{ borderTop: "1px solid #1f2430" }}>
                  <td style={{ padding: "0.3rem 0" }}>{p.fiscal_year}</td>
                  <td>{p.period_type}</td>
                  <td>{p.source}</td>
                  <td>{formatMoney(p.revenue)}</td>
                  <td>{formatMoney(p.ebitda)}</td>
                  <td>{formatMoney(p.operating_cash_flow)}</td>
                  <td>{formatMoney(p.capex)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function formatMoney(value: number | null): string {
  if (value === null) return "-";
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function sourceTagStyle(source: string): React.CSSProperties {
  const colors: Record<string, string> = {
    computed: "#3ecf8e",
    assumption: "#4f7cff",
    default: "#e0a030",
  };
  return {
    color: colors[source] || "#7c8494",
    border: `1px solid ${colors[source] || "#7c8494"}`,
    borderRadius: "4px",
    padding: "0.1rem 0.4rem",
    fontSize: "0.75rem",
  };
}

const inputStyle: React.CSSProperties = {
  padding: "0.4rem",
  borderRadius: "6px",
  border: "1px solid #2a3040",
  background: "#0b0e14",
  color: "#e6e6e6",
};

const buttonStyle: React.CSSProperties = {
  padding: "0.4rem 0.9rem",
  borderRadius: "6px",
  border: "none",
  background: "#4f7cff",
  color: "white",
  cursor: "pointer",
};
