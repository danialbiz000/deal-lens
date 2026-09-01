"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type CaseType, type LboCaseResponse, type SensitivityResponse } from "@/lib/api";

const cardStyle: React.CSSProperties = {
  border: "1px solid #1f2430",
  borderRadius: "8px",
  padding: "1rem",
  background: "#11151d",
};

const buttonStyle: React.CSSProperties = {
  padding: "0.4rem 0.9rem",
  borderRadius: "6px",
  border: "none",
  background: "#4f7cff",
  color: "white",
  cursor: "pointer",
};

const CASE_TYPES: CaseType[] = ["base", "bull", "bear"];

export default function LboPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [caseType, setCaseType] = useState<CaseType>("base");
  const [lboCase, setLboCase] = useState<LboCaseResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh(selectedCase: CaseType) {
    setError(null);
    try {
      setLboCase(await api.getLbo(companyId, selectedCase));
    } catch {
      setLboCase(null);
    }
    try {
      setSensitivity(await api.getLboSensitivity(companyId, selectedCase));
    } catch {
      setSensitivity(null);
    }
  }

  useEffect(() => {
    refresh(caseType);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId, caseType]);

  async function handleGenerateScenarios() {
    setBusy(true);
    setError(null);
    try {
      await api.generateScenarios(companyId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to generate scenarios");
    } finally {
      setBusy(false);
    }
  }

  async function handleRun() {
    setBusy(true);
    setError(null);
    try {
      await api.runLbo(companyId, caseType);
      await refresh(caseType);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to run LBO");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <Link href={`/companies/${companyId}`} style={{ color: "#7c8494" }}>
          &larr; back to company
        </Link>
      </div>

      <section style={cardStyle}>
        <h1 style={{ marginTop: 0 }}>LBO underwriting</h1>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
          {CASE_TYPES.map((ct) => (
            <button
              key={ct}
              onClick={() => setCaseType(ct)}
              style={{
                ...buttonStyle,
                background: ct === caseType ? "#4f7cff" : "#1f2430",
                textTransform: "uppercase",
              }}
            >
              {ct}
            </button>
          ))}
          <button onClick={handleGenerateScenarios} disabled={busy} style={buttonStyle}>
            Generate scenarios
          </button>
          <button onClick={handleRun} disabled={busy} style={buttonStyle}>
            {busy ? "Running..." : `Run ${caseType.toUpperCase()} case`}
          </button>
        </div>
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
      </section>

      {lboCase ? (
        <>
          <section style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Key outputs</h2>
            <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
              <Stat label="MOIC" value={`${lboCase.moic.toFixed(2)}x`} />
              <Stat label="IRR" value={`${(lboCase.irr * 100).toFixed(1)}%`} />
              <Stat label="Entry multiple" value={`${lboCase.entry_multiple.toFixed(1)}x`} />
              <Stat label="Exit multiple" value={`${lboCase.exit_multiple.toFixed(1)}x`} />
              <Stat label="Entry leverage" value={`${lboCase.entry_leverage.toFixed(1)}x`} />
              <Stat label="Exit leverage" value={`${lboCase.exit_leverage.toFixed(1)}x`} />
            </div>
            {lboCase.warnings.length > 0 && (
              <ul style={{ color: "#e0a030", fontSize: "0.85rem" }}>
                {lboCase.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </section>

          <section style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Sources &amp; Uses</h2>
            <table style={{ fontSize: "0.85rem" }}>
              <tbody>
                <tr>
                  <td style={{ paddingRight: "1rem", color: "#7c8494" }}>New debt</td>
                  <td>{formatMoney(lboCase.sources_uses.new_debt)}</td>
                </tr>
                <tr>
                  <td style={{ paddingRight: "1rem", color: "#7c8494" }}>Sponsor equity</td>
                  <td>{formatMoney(lboCase.sources_uses.sponsor_equity)}</td>
                </tr>
                <tr>
                  <td style={{ paddingRight: "1rem", color: "#7c8494" }}>Purchase EV</td>
                  <td>{formatMoney(lboCase.sources_uses.purchase_ev)}</td>
                </tr>
                <tr>
                  <td style={{ paddingRight: "1rem", color: "#7c8494" }}>Fees</td>
                  <td>{formatMoney(lboCase.sources_uses.fees)}</td>
                </tr>
                <tr>
                  <td style={{ paddingRight: "1rem", color: "#7c8494" }}>Reconciles</td>
                  <td style={{ color: lboCase.sources_uses.reconciles ? "#3ecf8e" : "#ff6b6b" }}>
                    {String(lboCase.sources_uses.reconciles)}
                  </td>
                </tr>
              </tbody>
            </table>
          </section>

          <section style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Value creation bridge</h2>
            {lboCase.value_creation_bridge.value_destructive && (
              <p style={{ color: "#ff6b6b" }}>Value-destructive case: this deal loses money on these assumptions.</p>
            )}
            {lboCase.value_creation_bridge.exit_multiple_dependent && (
              <p style={{ color: "#e0a030" }}>
                Exit-multiple dependent: &gt;50% of value creation relies on multiple expansion.
              </p>
            )}
            <BridgeBar label="Entry equity" value={lboCase.value_creation_bridge.entry_equity} />
            <BridgeBar label="EBITDA growth" value={lboCase.value_creation_bridge.ebitda_growth} />
            <BridgeBar label="Margin expansion" value={lboCase.value_creation_bridge.margin_expansion} />
            <BridgeBar label="Debt paydown" value={lboCase.value_creation_bridge.debt_paydown} />
            <BridgeBar label="Multiple expansion" value={lboCase.value_creation_bridge.multiple_expansion} />
            <BridgeBar label="Transaction fees" value={lboCase.value_creation_bridge.transaction_fees} />
            <p style={{ color: "#7c8494", fontSize: "0.8rem" }}>
              Total: {lboCase.value_creation_bridge.total.toFixed(3)}x (reconciles exactly to MOIC{" "}
              {lboCase.moic.toFixed(3)}x)
            </p>
          </section>

          <section style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Debt schedule</h2>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
              <thead>
                <tr style={{ textAlign: "left", color: "#7c8494" }}>
                  <th>Yr</th>
                  <th>Revenue</th>
                  <th>EBITDA</th>
                  <th>Interest</th>
                  <th>CFADS</th>
                  <th>Sweep</th>
                  <th>Ending debt</th>
                  <th>Ending cash</th>
                </tr>
              </thead>
              <tbody>
                {lboCase.schedule.map((y) => (
                  <tr key={y.year} style={{ borderTop: "1px solid #1f2430" }}>
                    <td>{y.year}</td>
                    <td>{formatMoney(y.revenue)}</td>
                    <td>{formatMoney(y.ebitda)}</td>
                    <td>{y.interest !== null ? formatMoney(y.interest) : "-"}</td>
                    <td>{y.cfads !== null ? formatMoney(y.cfads) : "-"}</td>
                    <td>{y.sweep !== null ? formatMoney(y.sweep) : "-"}</td>
                    <td>{formatMoney(y.ending_debt)}</td>
                    <td style={{ color: y.ending_cash < 0 ? "#ff6b6b" : undefined }}>{formatMoney(y.ending_cash)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : (
        <section style={cardStyle}>
          <p style={{ color: "#7c8494" }}>
            No {caseType.toUpperCase()} case computed yet -- generate scenarios, then click &quot;Run{" "}
            {caseType.toUpperCase()} case&quot; above. Requires the target to have &gt;=2 SELECTED peers (see the{" "}
            <Link href={`/companies/${companyId}/valuation`} style={{ color: "#4f7cff" }}>
              valuation page
            </Link>
            ) or an explicit entry_ev override.
          </p>
        </section>
      )}

      {sensitivity && (
        <section style={cardStyle}>
          <h2 style={{ marginTop: 0 }}>Entry x exit multiple sensitivity (IRR)</h2>
          <table style={{ borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead>
              <tr>
                <th style={{ padding: "0.3rem" }}></th>
                {sensitivity.exit_multiples.map((m, i) => (
                  <th key={i} style={{ padding: "0.3rem", color: "#7c8494" }}>
                    exit {m.toFixed(1)}x
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sensitivity.irr_grid.map((row, i) => (
                <tr key={i} style={{ borderTop: "1px solid #1f2430" }}>
                  <td style={{ padding: "0.3rem", color: "#7c8494" }}>
                    entry {sensitivity.entry_multiples[i].toFixed(1)}x
                  </td>
                  {row.map((irr, j) => (
                    <td key={j} style={{ padding: "0.3rem", textAlign: "center" }}>
                      {(irr * 100).toFixed(1)}%
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>{label}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function BridgeBar({ label, value }: { label: string; value: number }) {
  const width = Math.min(Math.abs(value) * 40, 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", margin: "0.25rem 0" }}>
      <div style={{ width: "160px", fontSize: "0.8rem", color: "#7c8494" }}>{label}</div>
      <div style={{ flex: 1, background: "#1f2430", borderRadius: "4px", height: "12px", position: "relative" }}>
        <div
          style={{
            width: `${width}%`,
            height: "100%",
            borderRadius: "4px",
            background: value >= 0 ? "#3ecf8e" : "#ff6b6b",
          }}
        />
      </div>
      <div style={{ width: "70px", textAlign: "right", fontSize: "0.8rem" }}>{value.toFixed(3)}x</div>
    </div>
  );
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}
