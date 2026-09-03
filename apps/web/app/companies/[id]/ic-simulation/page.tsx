"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type IcSimulationResponse, type IcSimulationSummary } from "@/lib/api";
import {
  Badge,
  Banner,
  Button,
  Card,
  CompanySubNav,
  EmptyState,
  Eyebrow,
  Skeleton,
  colors,
  recommendationTone,
} from "@/lib/ui";

const ROLE_LABELS: Record<string, string> = {
  analyst: "Analyst",
  industry: "Industry",
  credit: "Credit",
  risk: "Risk",
  ic_chair: "IC Chair",
};

export default function IcSimulationPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [summaries, setSummaries] = useState<IcSimulationSummary[]>([]);
  const [simulation, setSimulation] = useState<IcSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function refresh() {
    setError(null);
    try {
      const list = await api.listIcSimulations(companyId);
      setSummaries(list);
      if (list.length > 0) {
        setSimulation(await api.getIcSimulation(companyId, list[0].version));
      } else {
        setSimulation(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to load IC simulation");
    } finally {
      setLoaded(true);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleGenerate() {
    setBusy(true);
    setError(null);
    try {
      await api.generateIcSimulation(companyId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to run IC simulation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <Eyebrow>AI layer</Eyebrow>
        <h1 style={{ margin: 0, fontSize: "1.4rem" }}>Investment Committee simulation</h1>
      </div>

      <CompanySubNav companyId={companyId} active="ic" />

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <p style={{ color: colors.textFaint, fontSize: "0.85rem", margin: 0, maxWidth: "560px" }}>
            Requires screening, valuation, and BASE/BULL/BEAR LBO cases all present. Runs 5 sequential
            Claude calls (Analyst &rarr; Industry &rarr; Credit &rarr; Risk &rarr; IC Chair), then applies a
            deterministic bear-case threshold check in code -- the model can never talk its way past it.
          </p>
          <Button onClick={handleGenerate} disabled={busy}>
            {busy ? "Running 5 roles..." : "Run new IC simulation"}
          </Button>
        </div>
        {error && (
          <div style={{ marginTop: "0.75rem" }}>
            <Badge tone="danger">{error}</Badge>
          </div>
        )}
      </Card>

      {!loaded ? (
        <Skeleton height="12rem" />
      ) : simulation ? (
        <>
          {simulation.override_fired && (
            <Banner tone="warning" title="Recommendation overridden">
              <p style={{ color: colors.warning, fontSize: "0.9rem" }}>
                The model recommended <strong>{simulation.llm_recommendation}</strong>, but the bear case
                failed one or more deterministic thresholds, so the final recommendation was forced to{" "}
                <strong>HOLD</strong>.
              </p>
              {simulation.override_reason && (
                <p style={{ color: colors.textFaint, fontSize: "0.85rem", marginBottom: 0 }}>{simulation.override_reason}</p>
              )}
            </Banner>
          )}

          <Card>
            <div style={{ display: "flex", gap: "2rem", alignItems: "baseline", flexWrap: "wrap" }}>
              <div>
                <div style={{ color: colors.textMuted, fontSize: "0.72rem", fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase" }}>
                  Final recommendation
                </div>
                <div style={{ marginTop: "0.25rem" }}>
                  <Badge tone={recommendationTone(simulation.recommendation)}>
                    <span style={{ fontSize: "0.95rem" }}>{simulation.recommendation}</span>
                  </Badge>
                </div>
              </div>
              {simulation.llm_recommendation !== simulation.recommendation && (
                <div>
                  <div style={{ color: colors.textMuted, fontSize: "0.72rem", fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase" }}>
                    Model&apos;s raw recommendation
                  </div>
                  <div style={{ fontSize: "0.95rem", color: colors.textFaint, textDecoration: "line-through", marginTop: "0.3rem" }}>
                    {simulation.llm_recommendation}
                  </div>
                </div>
              )}
            </div>
            <p style={{ color: colors.textFaint, fontSize: "0.78rem", marginTop: "0.9rem", marginBottom: 0 }}>
              v{simulation.version} &middot; {simulation.model} &middot; generated {simulation.generated_at}
            </p>

            <div style={{ display: "flex", gap: "2rem", marginTop: "1.25rem", flexWrap: "wrap" }}>
              <IcList title="Key strengths" tone="success" items={simulation.key_strengths} />
              <IcList title="Key risks" tone="danger" items={simulation.key_risks} />
              <IcList title="Unanswered DD" tone="warning" items={simulation.unanswered_dd} />
            </div>
          </Card>

          <Card>
            <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Transcript</h2>
            {simulation.transcript.map((entry, i) => (
              <div
                key={i}
                style={{
                  borderTop: i > 0 ? `1px solid ${colors.border}` : undefined,
                  paddingTop: i > 0 ? "0.9rem" : 0,
                  marginTop: i > 0 ? "0.9rem" : 0,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
                  <strong style={{ fontSize: "0.88rem" }}>{ROLE_LABELS[entry.role] || entry.role}</strong>
                  {entry.validation_report.status === "warnings" && <Badge tone="warning">citation warnings</Badge>}
                </div>
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    fontSize: "0.8rem",
                    color: colors.text,
                    background: colors.bg,
                    border: `1px solid ${colors.border}`,
                    padding: "0.6rem 0.75rem",
                    borderRadius: "6px",
                    margin: 0,
                  }}
                >
                  {JSON.stringify(entry.output, null, 2)}
                </pre>
              </div>
            ))}
          </Card>
        </>
      ) : (
        <Card>
          <EmptyState>No IC simulation run yet -- click &quot;Run new IC simulation&quot; above.</EmptyState>
        </Card>
      )}
    </div>
  );
}

function IcList({ title, tone, items }: { title: string; tone: "success" | "danger" | "warning"; items: string[] }) {
  return (
    <div style={{ flex: "1 1 220px", minWidth: "220px" }}>
      <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.82rem", color: colors[tone] }}>{title}</h4>
      {items.length === 0 ? (
        <p style={{ color: colors.textFaint, fontSize: "0.82rem", margin: 0 }}>None</p>
      ) : (
        <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem", color: colors.text, lineHeight: 1.5 }}>
          {items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
