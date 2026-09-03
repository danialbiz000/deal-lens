"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type CaseType, type LboCaseResponse, type SensitivityResponse } from "@/lib/api";
import {
  Badge,
  Banner,
  Button,
  Card,
  CompanySubNav,
  EmptyState,
  Eyebrow,
  Skeleton,
  StatTile,
  colors,
  formatMoney,
  formatMultiple,
  formatPercent,
  thStyle,
  tdStyle,
  trStyle,
  type Tone,
} from "@/lib/ui";

const CASE_TYPES: CaseType[] = ["base", "bull", "bear"];

const CASE_TONE: Record<CaseType, Tone> = { base: "info", bull: "success", bear: "danger" };

function irrTone(irr: number): Tone {
  if (irr >= 0.18) return "success";
  if (irr >= 0.1) return "warning";
  return "danger";
}

export default function LboPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [caseType, setCaseType] = useState<CaseType>("base");
  const [lboCase, setLboCase] = useState<LboCaseResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function refresh(selectedCase: CaseType) {
    setError(null);
    setLoaded(false);
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
    setLoaded(true);
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
        <Eyebrow>Underwriting</Eyebrow>
        <h1 style={{ margin: 0, fontSize: "1.4rem" }}>LBO</h1>
      </div>

      <CompanySubNav companyId={companyId} active="lbo" />

      <Card>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: "0.4rem" }}>
            {CASE_TYPES.map((ct) => (
              <button
                key={ct}
                onClick={() => setCaseType(ct)}
                style={{
                  padding: "0.4rem 0.9rem",
                  borderRadius: "7px",
                  fontWeight: 700,
                  fontSize: "0.78rem",
                  letterSpacing: "0.03em",
                  textTransform: "uppercase",
                  cursor: "pointer",
                  border: `1px solid ${ct === caseType ? colors.accent : colors.border}`,
                  background: ct === caseType ? colors.accentSoft : "transparent",
                  color: ct === caseType ? colors.text : colors.textMuted,
                }}
              >
                {ct}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <Button variant="secondary" onClick={handleGenerateScenarios} disabled={busy}>
              Generate scenarios
            </Button>
            <Button onClick={handleRun} disabled={busy}>
              {busy ? "Running..." : `Run ${caseType.toUpperCase()} case`}
            </Button>
          </div>
        </div>
        {error && (
          <div style={{ marginTop: "0.75rem" }}>
            <Badge tone="danger">{error}</Badge>
          </div>
        )}
      </Card>

      {!loaded ? (
        <Skeleton height="10rem" />
      ) : lboCase ? (
        <>
          <Card tone={CASE_TONE[caseType]}>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Key outputs</h2>
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <StatTile label="MOIC" value={formatMultiple(lboCase.moic)} tone={CASE_TONE[caseType]} />
              <StatTile label="IRR" value={formatPercent(lboCase.irr)} tone={irrTone(lboCase.irr)} />
              <StatTile label="Entry multiple" value={formatMultiple(lboCase.entry_multiple, 1)} />
              <StatTile label="Exit multiple" value={formatMultiple(lboCase.exit_multiple, 1)} />
              <StatTile label="Entry leverage" value={formatMultiple(lboCase.entry_leverage, 1)} />
              <StatTile label="Exit leverage" value={formatMultiple(lboCase.exit_leverage, 1)} />
            </div>
            {lboCase.warnings.length > 0 && (
              <ul style={{ color: colors.warning, fontSize: "0.85rem" }}>
                {lboCase.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Sources &amp; Uses</h2>
            <table>
              <tbody>
                <tr>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>New debt</td>
                  <td style={tdStyle}>{formatMoney(lboCase.sources_uses.new_debt)}</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>Sponsor equity</td>
                  <td style={tdStyle}>{formatMoney(lboCase.sources_uses.sponsor_equity)}</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>Purchase EV</td>
                  <td style={tdStyle}>{formatMoney(lboCase.sources_uses.purchase_ev)}</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>Fees</td>
                  <td style={tdStyle}>{formatMoney(lboCase.sources_uses.fees)}</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: colors.textMuted }}>Reconciles</td>
                  <td style={tdStyle}>
                    <Badge tone={lboCase.sources_uses.reconciles ? "success" : "danger"}>
                      {String(lboCase.sources_uses.reconciles)}
                    </Badge>
                  </td>
                </tr>
              </tbody>
            </table>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Value creation bridge</h2>
            {lboCase.value_creation_bridge.value_destructive && (
              <div style={{ marginBottom: "0.75rem" }}>
                <Banner tone="danger" title="Value-destructive case">
                  This deal loses money on these assumptions.
                </Banner>
              </div>
            )}
            {lboCase.value_creation_bridge.exit_multiple_dependent && (
              <div style={{ marginBottom: "0.75rem" }}>
                <Banner tone="warning" title="Exit-multiple dependent">
                  &gt;50% of value creation relies on multiple expansion.
                </Banner>
              </div>
            )}
            <BridgeBar label="Entry equity" value={lboCase.value_creation_bridge.entry_equity} />
            <BridgeBar label="EBITDA growth" value={lboCase.value_creation_bridge.ebitda_growth} />
            <BridgeBar label="Margin expansion" value={lboCase.value_creation_bridge.margin_expansion} />
            <BridgeBar label="Debt paydown" value={lboCase.value_creation_bridge.debt_paydown} />
            <BridgeBar label="Multiple expansion" value={lboCase.value_creation_bridge.multiple_expansion} />
            <BridgeBar label="Transaction fees" value={lboCase.value_creation_bridge.transaction_fees} />
            <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginBottom: 0 }}>
              Total: {formatMultiple(lboCase.value_creation_bridge.total, 3)} (reconciles exactly to MOIC{" "}
              {formatMultiple(lboCase.moic, 3)})
            </p>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Debt schedule</h2>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th style={thStyle}>Yr</th>
                    <th style={thStyle}>Revenue</th>
                    <th style={thStyle}>EBITDA</th>
                    <th style={thStyle}>Interest</th>
                    <th style={thStyle}>CFADS</th>
                    <th style={thStyle}>Sweep</th>
                    <th style={thStyle}>Ending debt</th>
                    <th style={thStyle}>Ending cash</th>
                  </tr>
                </thead>
                <tbody>
                  {lboCase.schedule.map((y) => (
                    <tr key={y.year} style={trStyle}>
                      <td style={tdStyle}>{y.year}</td>
                      <td style={tdStyle}>{formatMoney(y.revenue)}</td>
                      <td style={tdStyle}>{formatMoney(y.ebitda)}</td>
                      <td style={tdStyle}>{y.interest !== null ? formatMoney(y.interest) : "–"}</td>
                      <td style={tdStyle}>{y.cfads !== null ? formatMoney(y.cfads) : "–"}</td>
                      <td style={tdStyle}>{y.sweep !== null ? formatMoney(y.sweep) : "–"}</td>
                      <td style={tdStyle}>{formatMoney(y.ending_debt)}</td>
                      <td style={{ ...tdStyle, color: y.ending_cash < 0 ? colors.danger : undefined }}>
                        {formatMoney(y.ending_cash)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      ) : (
        <Card>
          <EmptyState>
            No {caseType.toUpperCase()} case computed yet -- generate scenarios, then click &quot;Run{" "}
            {caseType.toUpperCase()} case&quot; above. Requires the target to have &ge;2 SELECTED peers (see the{" "}
            <Link href={`/companies/${companyId}/valuation`} style={{ color: colors.accent }}>
              valuation page
            </Link>
            ) or an explicit entry_ev override.
          </EmptyState>
        </Card>
      )}

      {sensitivity && (
        <Card>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Entry &times; exit multiple sensitivity (IRR)</h2>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th style={thStyle}></th>
                  {sensitivity.exit_multiples.map((m, i) => (
                    <th key={i} style={{ ...thStyle, textAlign: "center" }}>
                      exit {m.toFixed(1)}x
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sensitivity.irr_grid.map((row, i) => (
                  <tr key={i} style={trStyle}>
                    <td style={{ ...tdStyle, color: colors.textMuted }}>entry {sensitivity.entry_multiples[i].toFixed(1)}x</td>
                    {row.map((irr, j) => {
                      const tone = irrTone(irr);
                      return (
                        <td key={j} style={{ padding: "0.25rem" }}>
                          <div
                            style={{
                              textAlign: "center",
                              borderRadius: "6px",
                              padding: "0.35rem 0.4rem",
                              fontWeight: 600,
                              fontSize: "0.82rem",
                              background: tone === "success" ? colors.successSoft : tone === "warning" ? colors.warningSoft : colors.dangerSoft,
                              color: tone === "success" ? colors.success : tone === "warning" ? colors.warning : colors.danger,
                            }}
                          >
                            {formatPercent(irr)}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function BridgeBar({ label, value }: { label: string; value: number }) {
  const width = Math.min(Math.abs(value) * 40, 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", margin: "0.3rem 0" }}>
      <div style={{ width: "150px", fontSize: "0.8rem", color: colors.textMuted }}>{label}</div>
      <div style={{ flex: 1, background: colors.surfaceRaised, borderRadius: "4px", height: "10px", position: "relative" }}>
        <div
          style={{
            width: `${width}%`,
            height: "100%",
            borderRadius: "4px",
            background: value >= 0 ? colors.success : colors.danger,
          }}
        />
      </div>
      <div style={{ width: "70px", textAlign: "right", fontSize: "0.8rem", fontVariantNumeric: "tabular-nums" }}>
        {formatMultiple(value, 3)}
      </div>
    </div>
  );
}
