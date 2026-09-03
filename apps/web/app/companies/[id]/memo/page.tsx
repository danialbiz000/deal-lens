"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type MemoResponse, type MemoSummary } from "@/lib/api";
import { Badge, Banner, Button, Card, CompanySubNav, EmptyState, Eyebrow, Skeleton, colors } from "@/lib/ui";

export default function MemoPage({ params }: { params: { id: string } }) {
  const companyId = params.id;

  const [summaries, setSummaries] = useState<MemoSummary[]>([]);
  const [memo, setMemo] = useState<MemoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

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
        <Eyebrow>AI layer</Eyebrow>
        <h1 style={{ margin: 0, fontSize: "1.4rem" }}>Investment memo</h1>
      </div>

      <CompanySubNav companyId={companyId} active="memo" />

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
          <p style={{ color: colors.textFaint, fontSize: "0.85rem", margin: 0, maxWidth: "560px" }}>
            Requires a screening score, a valuation with &ge;2 selected peers, and a BASE LBO case. This is
            the only page that makes a real outbound call to a third-party API (Claude, for narrative
            synthesis only -- every number is pulled from the deterministic engine, never computed by the model).
          </p>
          <Button onClick={handleGenerate} disabled={busy}>
            {busy ? "Generating..." : "Generate new memo version"}
          </Button>
        </div>
        {error && (
          <div style={{ marginTop: "0.75rem" }}>
            <Badge tone="danger">{error}</Badge>
          </div>
        )}
        {summaries.length > 1 && (
          <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginBottom: 0, marginTop: "0.6rem" }}>
            {summaries.length} versions exist. Showing the latest (v{summaries[0].version}).
          </p>
        )}
      </Card>

      {!loaded ? (
        <Skeleton height="12rem" />
      ) : memo ? (
        <>
          {memo.validation_report.status === "warnings" && (
            <Banner tone="warning" title="Citation warnings">
              <CitationList
                label="Invalid citations (path not found in source data)"
                items={memo.validation_report.invalid_citations}
                tone="danger"
              />
              <CitationList
                label="Mismatched citations (stated number doesn't match the cited value)"
                items={memo.validation_report.mismatched_citations}
                tone="danger"
              />
              <CitationList
                label="Uncited numbers (heuristic, may include false positives)"
                items={memo.validation_report.uncited_numbers}
                tone="warning"
                last
              />
            </Banner>
          )}

          <Card>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center", marginBottom: "1rem" }}>
              <Badge tone={memo.validation_report.status === "ok" ? "success" : "warning"}>
                {memo.validation_report.status === "ok" ? "citations clean" : "citation warnings"}
              </Badge>
              <span style={{ color: colors.textFaint, fontSize: "0.78rem" }}>
                v{memo.version} &middot; {memo.model} &middot; prompt {memo.prompt_version} &middot; {memo.generated_at}
              </span>
            </div>
            {memo.sections.map((section) => (
              <div key={section.section_key} style={{ marginBottom: "1.4rem" }}>
                <h3 style={{ marginBottom: "0.35rem", fontSize: "0.95rem" }}>{section.title}</h3>
                <p style={{ whiteSpace: "pre-wrap", color: colors.text, lineHeight: 1.55, margin: 0, fontSize: "0.9rem" }}>
                  {section.content}
                </p>
              </div>
            ))}
          </Card>
        </>
      ) : (
        <Card>
          <EmptyState>No memo generated yet -- click &quot;Generate new memo version&quot; above.</EmptyState>
        </Card>
      )}
    </div>
  );
}

function CitationList({
  label,
  items,
  tone,
  last,
}: {
  label: string;
  items: string[];
  tone: "danger" | "warning";
  last?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <div style={{ marginBottom: last ? 0 : "0.9rem" }}>
      <div style={{ color: colors[tone], fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem" }}>
        {label} ({items.length})
      </div>
      <ul
        style={{
          margin: 0,
          paddingLeft: "1.1rem",
          maxHeight: "9rem",
          overflowY: "auto",
          fontSize: "0.8rem",
          color: colors.textMuted,
          lineHeight: 1.6,
        }}
      >
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
