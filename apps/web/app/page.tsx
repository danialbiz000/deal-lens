"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type Company } from "@/lib/api";

const cardStyle: React.CSSProperties = {
  border: "1px solid #1f2430",
  borderRadius: "8px",
  padding: "1rem",
  background: "#11151d",
};

export default function CompanyListPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [ticker, setTicker] = useState("");
  const [name, setName] = useState("");
  const [cik, setCik] = useState("");
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
      await api.createCompany({ ticker, name, cik: cik || undefined });
      setTicker("");
      setName("");
      setCik("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "failed to create company");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <section style={cardStyle}>
        <h2 style={{ marginTop: 0 }}>Add a company</h2>
        <form onSubmit={handleCreate} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          <input
            placeholder="Ticker (e.g. AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            required
            style={inputStyle}
          />
          <input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={inputStyle}
          />
          <input
            placeholder="CIK (optional, e.g. 0000320193)"
            value={cik}
            onChange={(e) => setCik(e.target.value)}
            style={inputStyle}
          />
          <button type="submit" disabled={submitting} style={buttonStyle}>
            {submitting ? "Adding..." : "Add company"}
          </button>
        </form>
        <p style={{ color: "#7c8494", fontSize: "0.85rem" }}>
          A CIK is required before <code>/ingest</code> can pull SEC EDGAR data for this company.
        </p>
      </section>

      {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

      <section>
        <h2>Companies</h2>
        {loading ? (
          <p>Loading...</p>
        ) : companies.length === 0 ? (
          <p style={{ color: "#7c8494" }}>No companies yet -- add one above.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {companies.map((c) => (
              <Link
                key={c.id}
                href={`/companies/${c.id}`}
                style={{ ...cardStyle, display: "block", color: "#e6e6e6", textDecoration: "none" }}
              >
                <strong>{c.ticker}</strong> -- {c.name}
                {c.sector && <span style={{ color: "#7c8494" }}> &middot; {c.sector}</span>}
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  padding: "0.5rem",
  borderRadius: "6px",
  border: "1px solid #2a3040",
  background: "#0b0e14",
  color: "#e6e6e6",
  flex: "1 1 160px",
};

const buttonStyle: React.CSSProperties = {
  padding: "0.5rem 1rem",
  borderRadius: "6px",
  border: "none",
  background: "#4f7cff",
  color: "white",
  cursor: "pointer",
};
