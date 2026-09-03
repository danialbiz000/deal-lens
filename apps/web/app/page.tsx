"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type Company } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Eyebrow, Skeleton, colors, inputStyle } from "@/lib/ui";

export default function CompanyListPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [cik, setCik] = useState("");
  const [sector, setSector] = useState("");
  const [industry, setIndustry] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setCompanies(await api.listCompanies());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to load companies");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createCompany({
        ticker,
        name,
        cik: cik || undefined,
        sector: sector || undefined,
        industry: industry || undefined,
      });
      setTicker("");
      setName("");
      setCik("");
      setSector("");
      setIndustry("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to create company");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <div>
        <Eyebrow>Deal screening</Eyebrow>
        <h1 style={{ margin: 0, fontSize: "1.5rem" }}>Companies</h1>
      </div>

      <Card>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Add a company</h2>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
          <input
            placeholder="Ticker (e.g. AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            required
            style={{ ...inputStyle, flex: "1 1 160px" }}
          />
          <input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ ...inputStyle, flex: "1 1 200px" }}
          />
          <input
            placeholder="CIK (optional, e.g. 0000320193)"
            value={cik}
            onChange={(e) => setCik(e.target.value)}
            style={{ ...inputStyle, flex: "1 1 200px" }}
          />
          <input
            placeholder="Sector (optional, e.g. Technology)"
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            style={{ ...inputStyle, flex: "1 1 200px" }}
          />
          <input
            placeholder="Industry (optional, e.g. Consumer Electronics)"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            style={{ ...inputStyle, flex: "1 1 220px" }}
          />
          <Button type="submit" disabled={submitting}>
            {submitting ? "Adding..." : "Add company"}
          </Button>
        </form>
        <p style={{ color: colors.textFaint, fontSize: "0.8rem", marginBottom: 0 }}>
          A CIK is required before ingest can pull SEC EDGAR data for this company. Sector is required before
          peer generation (Valuation tab) can run.
        </p>
      </Card>

      {error && <Badge tone="danger">{error}</Badge>}

      <div>
        <h2 style={{ fontSize: "0.95rem", color: colors.textMuted, marginBottom: "0.75rem" }}>
          {loading ? "Loading..." : `${companies.length} ${companies.length === 1 ? "company" : "companies"}`}
        </h2>
        {loading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <Skeleton height="3.2rem" />
            <Skeleton height="3.2rem" />
          </div>
        ) : companies.length === 0 ? (
          <EmptyState>No companies yet -- add one above to start a screening case.</EmptyState>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {companies.map((c) => (
              <Link key={c.id} href={`/companies/${c.id}`} style={{ textDecoration: "none" }}>
                <div
                  style={{
                    border: `1px solid ${colors.border}`,
                    borderRadius: "8px",
                    padding: "0.85rem 1.1rem",
                    background: colors.surface,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "1rem",
                  }}
                >
                  <div>
                    <strong style={{ color: colors.text }}>{c.ticker}</strong>{" "}
                    <span style={{ color: colors.textMuted }}>{c.name}</span>
                    {c.sector && <span style={{ color: colors.textFaint }}> &middot; {c.sector}</span>}
                  </div>
                  <Badge tone={c.cik ? "success" : "neutral"}>{c.cik ? "ready to ingest" : "no CIK yet"}</Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
