"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type Peer, type ValuationResponse } from "@/lib/api";

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

function statusColor(status: string): string {
  if (status === "SELECTED") return "#3ecf8e";
  if (status === "REJECTED") return "#ff6b6b";
  return "#e0a030";
}

export default function ValuationPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [peers, setPeers] = useState<Peer[]>([]);
  const [valuation, setValuation] = useState<ValuationResponse | null>(null);
  const [valuationError, setValuationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setPeers(await api.listPeers(companyId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to load peers");
    }
    try {
      setValuation(await api.getValuation(companyId));
      setValuationError(null);
    } catch (err) {
      setValuation(null);
      setValuationError(err instanceof ApiError ? err.message : "failed to load valuation");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleGeneratePeers() {
    setBusy(true);
    setError(null);
    try {
      await api.generatePeers(companyId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to generate peers");
    } finally {
      setBusy(false);
    }
  }

  async function handleOverride(peer: Peer, status: "SELECTED" | "REJECTED") {
    const reason = window.prompt(`Reason for marking ${peer.peer_ticker} as ${status}:`);
    if (!reason) return;
    setBusy(true);
    try {
      await api.patchPeer(companyId, peer.id, { status, reason_notes: reason });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to override peer");
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
        <h1 style={{ marginTop: 0 }}>Comparable companies &amp; valuation</h1>
        <button onClick={handleGeneratePeers} disabled={busy} style={buttonStyle}>
          {busy ? "Working..." : "Generate / refresh peers"}
        </button>
        <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
          Peer universe = companies already ingested into DealLens (no external screener in this slice).
          Every candidate stays visible even when rejected -- peer selection is never silently accepted.
        </p>
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
      </section>

      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Entry valuation</h2>
        {valuationError ? (
          <p style={{ color: "#e0a030" }}>{valuationError}</p>
        ) : valuation ? (
          <>
            <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
              <div>
                <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Entry EV (from EV/EBITDA median)</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{formatMoney(valuation.entry_ev)}</div>
              </div>
              <div>
                <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Entry equity value</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{formatMoney(valuation.entry_equity_value)}</div>
              </div>
              <div>
                <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Median EV/EBITDA</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{valuation.median_ev_ebitda.toFixed(2)}x</div>
              </div>
              <div>
                <div style={{ color: "#7c8494", fontSize: "0.8rem" }}>Median EV/Revenue (cross-check only)</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{valuation.median_ev_revenue.toFixed(2)}x</div>
              </div>
            </div>
            <p style={{ color: "#7c8494", fontSize: "0.8rem" }}>
              Based on {valuation.peer_count} SELECTED peer(s). Q1/Q3 EV/EBITDA: {valuation.q1_ev_ebitda.toFixed(2)}x
              &ndash; {valuation.q3_ev_ebitda.toFixed(2)}x.
            </p>
          </>
        ) : (
          <p>Loading...</p>
        )}
      </section>

      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Peers</h2>
        {peers.length === 0 ? (
          <p style={{ color: "#7c8494" }}>No peers yet -- click &quot;Generate / refresh peers&quot; above.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ textAlign: "left", color: "#7c8494" }}>
                <th>Peer</th>
                <th>Status</th>
                <th>Score</th>
                <th>EV/Rev</th>
                <th>EV/EBITDA</th>
                <th>Reason</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {peers.map((p) => (
                <tr key={p.id} style={{ borderTop: "1px solid #1f2430" }}>
                  <td style={{ padding: "0.4rem 0" }}>
                    {p.peer_ticker} <span style={{ color: "#7c8494" }}>{p.peer_name}</span>
                  </td>
                  <td>
                    <span style={{ color: statusColor(p.status) }}>{p.status}</span>
                  </td>
                  <td>{p.similarity_score ?? "-"}</td>
                  <td>{p.ev_revenue_multiple?.toFixed(2) ?? "-"}</td>
                  <td>{p.ev_ebitda_multiple?.toFixed(2) ?? "-"}</td>
                  <td style={{ color: "#7c8494" }}>{p.reason_code || p.reason_notes || "-"}</td>
                  <td>
                    {p.status !== "SELECTED" && (
                      <button onClick={() => handleOverride(p, "SELECTED")} disabled={busy} style={{ ...buttonStyle, fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}>
                        Select
                      </button>
                    )}
                    {p.status !== "REJECTED" && (
                      <button onClick={() => handleOverride(p, "REJECTED")} disabled={busy} style={{ ...buttonStyle, fontSize: "0.75rem", padding: "0.2rem 0.5rem", background: "#ff6b6b" }}>
                        Reject
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}
