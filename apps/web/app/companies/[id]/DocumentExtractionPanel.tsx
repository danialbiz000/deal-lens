"use client";

import { useState } from "react";
import { api, ApiError, type ExtractedPeriodCandidate } from "@/lib/api";
import { Badge, Button, Card, colors, formatMoney } from "@/lib/ui";

/**
 * Split out of page.tsx purely to keep that file under this project's
 * 500-line limit -- owns the upload button + AI-extraction results, and
 * hands a chosen candidate back to the parent (which owns the manual-entry
 * form the candidate gets prefilled into, since that form already existed
 * before this feature and is shared with typed-in entries too).
 */
export function DocumentExtractionPanel({
  companyId,
  onUseCandidate,
}: {
  companyId: string;
  onUseCandidate: (candidate: ExtractedPeriodCandidate) => void;
}) {
  const [extracting, setExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [extractedPeriods, setExtractedPeriods] = useState<ExtractedPeriodCandidate[]>([]);
  const [extractionNotes, setExtractionNotes] = useState<string | null>(null);

  async function handleExtractDocument(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setExtracting(true);
    setExtractionError(null);
    try {
      const result = await api.extractFinancialsFromDocument(companyId, file);
      setExtractedPeriods(result.periods);
      setExtractionNotes(result.notes);
    } catch (err) {
      setExtractedPeriods([]);
      setExtractionNotes(null);
      setExtractionError(err instanceof ApiError ? err.message : "extraction failed");
    } finally {
      setExtracting(false);
      e.target.value = "";
    }
  }

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.75rem" }}>
        <div style={{ color: colors.textMuted, fontSize: "0.85rem" }}>
          Upload a financial statement or investor-relations PDF and let AI propose the numbers -- nothing is saved
          until you review and confirm each figure below.
        </div>
        <label style={{ display: "inline-block" }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "0.45rem 0.9rem",
              borderRadius: "6px",
              border: `1px solid ${colors.border}`,
              color: colors.text,
              fontSize: "0.85rem",
              cursor: extracting ? "wait" : "pointer",
              opacity: extracting ? 0.6 : 1,
            }}
          >
            {extracting ? "Extracting..." : "Extract from document"}
          </span>
          <input
            type="file"
            accept="application/pdf"
            onChange={handleExtractDocument}
            disabled={extracting}
            style={{ display: "none" }}
          />
        </label>
      </div>

      {extractionError && (
        <div style={{ marginTop: "0.6rem" }}>
          <Badge tone="danger">{extractionError}</Badge>
        </div>
      )}

      {extractedPeriods.length > 0 && (
        <div style={{ marginTop: "1rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Extracted candidates -- review before saving</h2>
          {extractionNotes && (
            <p style={{ color: colors.textMuted, fontSize: "0.8rem", fontStyle: "italic" }}>{extractionNotes}</p>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {extractedPeriods.map((candidate, i) => (
              <div
                key={i}
                style={{
                  border: `1px solid ${colors.border}`,
                  borderRadius: "8px",
                  padding: "0.75rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "0.6rem",
                }}
              >
                <div style={{ fontSize: "0.85rem" }}>
                  <strong>
                    {candidate.period_type} {candidate.fiscal_year}
                  </strong>{" "}
                  <span style={{ color: colors.textFaint }}>
                    ({candidate.currency}, ends {candidate.period_end_date})
                  </span>
                  <div style={{ color: colors.textFaint, marginTop: "0.2rem" }}>
                    Revenue {formatMoney(candidate.revenue)} &middot; EBITDA {formatMoney(candidate.ebitda)}
                  </div>
                </div>
                <Button size="sm" onClick={() => onUseCandidate(candidate)}>
                  Review &amp; prefill form
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
