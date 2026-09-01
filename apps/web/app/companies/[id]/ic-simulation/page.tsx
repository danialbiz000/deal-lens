"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type IcSimulationResponse, type IcSimulationSummary } from "@/lib/api";

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

const ROLE_LABELS: Record<string, string> = {
  analyst: "Analyst",
  industry: "Industry",
  credit: "Credit",
  risk: "Risk",
  ic_chair: "IC Chair",
};

function recommendationColor(rec: string): string {
  if (rec === "PROCEED_TO_DD") return "#3ecf8e";
  if (rec === "HOLD") return "#e0a030";
  return "#ff6b6b";
}

export default function IcSimulationPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [summaries, setSummaries] = useState<IcSimulationSummary[]>([]);
  const [simulation, setSimulation] = useState<IcSimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
        <Link href={`/companies/${companyId}`} style={{ color: "#7c8494" }}>
          &larr; back to company
        </Link>
      </div>

      <section style={cardStyle}>
        <h1 style={{ marginTop: 0 }}>Investment Committee simulation</h1>
        <button onClick={handleGenerate} disabled={busy} style={buttonStyle}>
          {busy ? "Running 5 roles..." : "Run new IC simulation"}
        </button>
        <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
          Requires screening, valuation, and BASE/BULL/BEAR LBO cases all present. Runs 5 sequential
          Claude calls (Analyst &rarr; Industry &rarr; Credit &rarr; Risk &rarr; IC Chair), then applies a
          deterministic bear-case threshold check in code -- the model can never talk its way past it.
        </p>
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
      </section>

      {simulation && (
        <>
          {simulation.override_fired && (
            <section style={{ ...cardStyle, borderColor: "#e0a030", background: "#241c0f" }}>
              <strong style={{ color: "#e0a030" }}>Recommendation overridden</strong>
              <p style={{ color: "#e0a030", fontSize: "0.9rem" }}>
                The model recommended <strong>{simulation.llm_recommendation}</strong>, but the bear
                case failed one or more deterministic thresholds, so the final recommendation was
                forced to <strong>HOLD</strong>.
              </p>
              {simulation.override_reason && (
                <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>{simulation.override_reason}</p>
              )}
            </section>
          )}

          <section style={cardStyle}>
            <div style={{ display: "flex", gap: "2rem", alignItems: "baseline", flexWrap: "wrap" }}>
              <div>
                <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Final recommendation</div>
                <div style={{ fontSize: "1.75rem", fontWeight: 700, color: recommendationColor(simulation.recommendation) }}>
                  {simulation.recommendation}
                </div>
              </div>
              {simulation.llm_recommendation !== simulation.recommendation && (
                <div>
                  <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Model&apos;s raw recommendation</div>
                  <div style={{ fontSize: "1.1rem", color: "#7c8494", textDecoration: "line-through" }}>
                    {simulation.llm_recommendation}
                  </div>
                </div>
              )}
            </div>
            <p style={{ color: "#7c8494", fontSize: "0.8rem" }}>
              Version {simulation.version} &middot; model {simulation.model} &middot; generated{" "}
              {simulation.generated_at}
            </p>

            <div style={{ display: "flex", gap: "2rem", marginTop: "1rem", flexWrap: "wrap" }}>
              <div>
                <h4>Key strengths</h4>
                <ul>{simulation.key_strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
              <div>
                <h4>Key risks</h4>
                <ul>{simulation.key_risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </div>
              <div>
                <h4>Unanswered DD</h4>
                <ul>{simulation.unanswered_dd.map((d, i) => <li key={i}>{d}</li>)}</ul>
              </div>
            </div>
          </section>

          <section style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Transcript</h2>
            {simulation.transcript.map((entry, i) => (
              <div key={i} style={{ borderTop: i > 0 ? "1px solid #1f2430" : undefined, paddingTop: "0.75rem", marginTop: "0.75rem" }}>
                <strong>{ROLE_LABELS[entry.role] || entry.role}</strong>
                {entry.validation_report.status === "warnings" && (
                  <span style={{ color: "#e0a030", fontSize: "0.75rem", marginLeft: "0.5rem" }}>
                    (citation warnings)
                  </span>
                )}
                <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem", color: "#d0d4dc", background: "#0b0e14", padding: "0.5rem", borderRadius: "4px" }}>
                  {JSON.stringify(entry.output, null, 2)}
                </pre>
              </div>
            ))}
          </section>
        </>
      )}

      {!simulation && !error && <p style={{ color: "#7c8494" }}>No IC simulation run yet.</p>}
    </div>
  );
}
