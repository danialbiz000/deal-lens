"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type MemoResponse, type MemoSummary } from "@/lib/api";

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

export default function MemoPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [summaries, setSummaries] = useState<MemoSummary[]>([]);
  const [memo, setMemo] = useState<MemoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setError(null);
    try {
      const list = await api.listMemos(companyId);
      setSummaries(list);
      if (list.length > 0) {
        setMemo(await api.getMemo(companyId, list[0].version));
      } else {
        setMemo(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to load memo");
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
      await api.generateMemo(companyId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to generate memo");
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
        <h1 style={{ marginTop: 0 }}>Investment memo</h1>
        <button onClick={handleGenerate} disabled={busy} style={buttonStyle}>
          {busy ? "Generating..." : "Generate new memo version"}
        </button>
        <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
          Requires: a screening score, a valuation with &gt;=2 selected peers, and a BASE LBO case.
          Requires <code>ANTHROPIC_API_KEY</code> to be set on the server -- this is the only page in
          the app that makes a real outbound call to a third-party API.
        </p>
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
        {summaries.length > 1 && (
          <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
            {summaries.length} versions exist. Showing the latest (v{summaries[0].version}).
          </p>
        )}
      </section>

      {memo && (
        <>
          {memo.validation_report.status === "warnings" && (
            <section style={{ ...cardStyle, borderColor: "#e0a030" }}>
              <strong style={{ color: "#e0a030" }}>Citation warnings</strong>
              {memo.validation_report.invalid_citations.length > 0 && (
                <p style={{ color: "#ff6b6b", fontSize: "0.85rem" }}>
                  Invalid citations (path not found in source data): {memo.validation_report.invalid_citations.join(", ")}
                </p>
              )}
              {memo.validation_report.mismatched_citations.length > 0 && (
                <p style={{ color: "#ff6b6b", fontSize: "0.85rem" }}>
                  Mismatched citations (stated number doesn&apos;t match the cited value):{" "}
                  {memo.validation_report.mismatched_citations.join("; ")}
                </p>
              )}
              {memo.validation_report.uncited_numbers.length > 0 && (
                <p style={{ color: "#e0a030", fontSize: "0.85rem" }}>
                  Uncited numbers (heuristic, may include false positives): {memo.validation_report.uncited_numbers.join(", ")}
                </p>
              )}
            </section>
          )}

          <section style={cardStyle}>
            <p style={{ color: "#7c8494", fontSize: "0.8rem" }}>
              Version {memo.version} &middot; model {memo.model} &middot; prompt {memo.prompt_version} &middot;
              generated {memo.generated_at}
            </p>
            {memo.sections.map((section) => (
              <div key={section.section_key} style={{ marginBottom: "1.25rem" }}>
                <h3 style={{ marginBottom: "0.25rem" }}>{section.title}</h3>
                <p style={{ whiteSpace: "pre-wrap", color: "#d0d4dc" }}>{section.content}</p>
              </div>
            ))}
          </section>
        </>
      )}

      {!memo && !error && <p style={{ color: "#7c8494" }}>No memo generated yet.</p>}
    </div>
  );
}
