"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type Peer, type ValuationResponse } from "@/lib/api";
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
  formatMultiple,
  peerStatusTone,
  thStyle,
  tdStyle,
  trStyle,
} from "@/lib/ui";

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
        <Eyebrow>Comparable companies</Eyebrow>
        <h1 style={{ margin: 0, fontSize: "1.4rem" }}>Valuation</h1>
      </div>

      <CompanySubNav companyId={companyId} active="valuation" />

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <p style={{ color: colors.textFaint, fontSize: "0.85rem", margin: 0, maxWidth: "560px" }}>
            Peer universe = companies already ingested into DealLens (no external screener in this slice).
            Every candidate stays visible even when rejected -- peer selection is never silently accepted.
          </p>
          <Button onClick={handleGeneratePeers} disabled={busy}>
            {busy ? "Working..." : "Generate / refresh peers"}
          </Button>
        </div>
        {error && <Badge tone="danger">{error}</Badge>}
      </Card>

      <Card>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Entry valuation</h2>
        {valuationError ? (
          <Badge tone="warning">{valuationError}</Badge>
        ) : valuation ? (
          <>
            <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
              <StatTile label="Entry EV" value={formatMoney(valuation.entry_ev)} sub="from EV/EBITDA median" />
              <StatTile label="Entry equity value" value={formatMoney(valuation.entry_equity_value)} />
              <StatTile label="Median EV/EBITDA" value={formatMultiple(valuation.median_ev_ebitda)} />
              <StatTile label="Median EV/Revenue" value={formatMultiple(valuation.median_ev_revenue)} sub="cross-check only" />
            </div>
            <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginBottom: 0, marginTop: "0.9rem" }}>
              Based on {valuation.peer_count} SELECTED peer(s). Q1/Q3 EV/EBITDA: {formatMultiple(valuation.q1_ev_ebitda)}
              &ndash;{formatMultiple(valuation.q3_ev_ebitda)}.
            </p>
          </>
        ) : (
          <Skeleton height="5rem" />
        )}
      </Card>

      <Card>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Peers</h2>
        {peers.length === 0 ? (
          <EmptyState>No peers yet -- click &quot;Generate / refresh peers&quot; above.</EmptyState>
        ) : (
          <table style={{ width: "100%" }}>
            <thead>
              <tr>
                <th style={thStyle}>Peer</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Score</th>
                <th style={thStyle}>EV/Rev</th>
                <th style={thStyle}>EV/EBITDA</th>
                <th style={thStyle}>Reason</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {peers.map((p) => (
                <tr key={p.id} style={trStyle}>
                  <td style={tdStyle}>
                    <strong>{p.peer_ticker}</strong> <span style={{ color: colors.textFaint }}>{p.peer_name}</span>
                  </td>
                  <td style={tdStyle}>
                    <Badge tone={peerStatusTone(p.status)}>{p.status}</Badge>
                  </td>
                  <td style={tdStyle}>{p.similarity_score ?? "–"}</td>
                  <td style={tdStyle}>{p.ev_revenue_multiple !== null ? formatMultiple(p.ev_revenue_multiple) : "–"}</td>
                  <td style={tdStyle}>{p.ev_ebitda_multiple !== null ? formatMultiple(p.ev_ebitda_multiple) : "–"}</td>
                  <td style={{ ...tdStyle, color: colors.textFaint, fontSize: "0.78rem" }}>{p.reason_code || p.reason_notes || "–"}</td>
                  <td style={tdStyle}>
                    <div style={{ display: "flex", gap: "0.35rem" }}>
                      {p.status !== "SELECTED" && (
                        <Button size="sm" variant="secondary" onClick={() => handleOverride(p, "SELECTED")} disabled={busy}>
                          Select
                        </Button>
                      )}
                      {p.status !== "REJECTED" && (
                        <Button size="sm" variant="danger" onClick={() => handleOverride(p, "REJECTED")} disabled={busy}>
                          Reject
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
