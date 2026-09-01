import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "DealLens",
  description: "Phase 0 vertical slice: Company -> Financials -> Screening Score",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          margin: 0,
          background: "#0b0e14",
          color: "#e6e6e6",
        }}
      >
        <header
          style={{
            padding: "1rem 1.5rem",
            borderBottom: "1px solid #1f2430",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <Link href="/" style={{ color: "#e6e6e6", textDecoration: "none", fontWeight: 700, fontSize: "1.1rem" }}>
            DealLens
          </Link>
          <span style={{ color: "#7c8494", fontSize: "0.85rem" }}>
            Phase 0 slice -- Company &rarr; Financials &rarr; Screening Score
          </span>
        </header>
        <main style={{ padding: "1.5rem", maxWidth: "960px", margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}
