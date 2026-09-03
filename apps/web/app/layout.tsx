import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { colors } from "@/lib/theme";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "DealLens",
  description: "AI-assisted PE deal screening & underwriting -- deterministic finance engine + auditable AI layer",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body
        style={{
          margin: 0,
          background: colors.bg,
          color: colors.text,
          minHeight: "100vh",
        }}
      >
        <header
          style={{
            padding: "0.9rem 1.5rem",
            borderBottom: `1px solid ${colors.border}`,
            display: "flex",
            alignItems: "baseline",
            gap: "0.75rem",
            position: "sticky",
            top: 0,
            background: colors.bg,
            zIndex: 10,
          }}
        >
          <Link href="/" style={{ color: colors.text, textDecoration: "none", fontWeight: 800, fontSize: "1.05rem", letterSpacing: "-0.01em" }}>
            DealLens
          </Link>
          <span style={{ color: colors.textFaint, fontSize: "0.8rem" }}>
            Deterministic finance engine + auditable AI layer
          </span>
        </header>
        <main style={{ padding: "1.75rem 1.5rem 3rem", maxWidth: "1080px", margin: "0 auto" }}>{children}</main>
      </body>
    </html>
  );
}
