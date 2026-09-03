"use client";

/**
 * Shared visual language for the DealLens analyst workstation. Every page
 * under app/ imports from here instead of redefining its own cardStyle/
 * buttonStyle -- the point of this file is that navigating between Company,
 * Screening, Valuation, LBO, Memo, and IC Simulation should feel like one
 * continuous tool, not six unrelated pages (spec's own "one continuous
 * investment process" principle).
 */

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import {
  colors,
  formatMoney,
  formatMultiple,
  formatPercent,
  peerStatusTone,
  recommendationTone,
  scoreTone,
  sourceTone,
  toneColors,
  type Tone,
} from "@/lib/theme";

// Re-exported so existing page imports (`from "@/lib/ui"`) keep working
// unchanged -- ui.tsx is the single import surface for pages, theme.ts is
// just where the server-safe pieces physically live.
export {
  colors,
  formatMoney,
  formatMultiple,
  formatPercent,
  peerStatusTone,
  recommendationTone,
  scoreTone,
  sourceTone,
};
export type { Tone };

// ---------------------------------------------------------------------------
// Layout primitives
// ---------------------------------------------------------------------------

export function Card({
  children,
  tone,
  style,
}: {
  children: ReactNode;
  tone?: Tone;
  style?: CSSProperties;
}) {
  const borderColor = tone ? toneColors(tone).fg : colors.border;
  const background = tone ? toneColors(tone).bg : colors.surface;
  return (
    <section
      style={{
        border: `1px solid ${tone ? borderColor + "55" : colors.border}`,
        borderRadius: "10px",
        padding: "1.25rem",
        background: tone ? background : colors.surface,
        ...style,
      }}
    >
      {children}
    </section>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.9rem" }}>
      <h2 style={{ margin: 0, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em", color: colors.text }}>
        {children}
      </h2>
      {action}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: "0.72rem",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: colors.textFaint,
        marginBottom: "0.3rem",
      }}
    >
      {children}
    </div>
  );
}

export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      style={{
        color: colors.textMuted,
        textDecoration: "none",
        fontSize: "0.85rem",
        display: "inline-flex",
        alignItems: "center",
        gap: "0.35rem",
      }}
    >
      &larr; {children}
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Sub-navigation across the six company pages
// ---------------------------------------------------------------------------

const TABS = [
  { key: "overview", label: "Company", suffix: "" },
  { key: "valuation", label: "Valuation", suffix: "/valuation" },
  { key: "lbo", label: "LBO", suffix: "/lbo" },
  { key: "memo", label: "Memo", suffix: "/memo" },
  { key: "ic", label: "IC Simulation", suffix: "/ic-simulation" },
] as const;

export function CompanySubNav({
  companyId,
  active,
  ticker,
}: {
  companyId: string;
  active: (typeof TABS)[number]["key"];
  ticker?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.25rem",
        borderBottom: `1px solid ${colors.border}`,
        marginBottom: "1.5rem",
        overflowX: "auto",
      }}
    >
      {ticker && (
        <span
          style={{
            color: colors.textFaint,
            fontSize: "0.78rem",
            fontWeight: 700,
            letterSpacing: "0.04em",
            padding: "0.6rem 0.9rem 0.6rem 0",
            whiteSpace: "nowrap",
          }}
        >
          {ticker}
        </span>
      )}
      {TABS.map((tab) => {
        const isActive = tab.key === active;
        return (
          <Link
            key={tab.key}
            href={`/companies/${companyId}${tab.suffix}`}
            style={{
              padding: "0.6rem 0.9rem",
              fontSize: "0.85rem",
              fontWeight: isActive ? 700 : 500,
              color: isActive ? colors.text : colors.textMuted,
              textDecoration: "none",
              borderBottom: isActive ? `2px solid ${colors.accent}` : "2px solid transparent",
              marginBottom: "-1px",
              whiteSpace: "nowrap",
            }}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Stats / badges / buttons
// ---------------------------------------------------------------------------

export function StatTile({
  label,
  value,
  tone,
  sub,
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
  sub?: ReactNode;
}) {
  return (
    <div
      style={{
        border: `1px solid ${colors.border}`,
        borderRadius: "8px",
        padding: "0.85rem 1rem",
        background: colors.surfaceRaised,
        minWidth: "140px",
        flex: "1 1 140px",
      }}
    >
      <div style={{ color: colors.textMuted, fontSize: "0.72rem", fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.55rem", fontWeight: 700, color: tone ? toneColors(tone).fg : colors.text, marginTop: "0.15rem" }}>
        {value}
      </div>
      {sub && <div style={{ color: colors.textFaint, fontSize: "0.75rem", marginTop: "0.1rem" }}>{sub}</div>}
    </div>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  const { fg, bg } = toneColors(tone);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        color: fg,
        background: bg,
        border: `1px solid ${fg}33`,
        borderRadius: "999px",
        padding: "0.12rem 0.6rem",
        fontSize: "0.72rem",
        fontWeight: 600,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  children,
  variant = "primary",
  size = "md",
  disabled,
  onClick,
  type = "button",
}: {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: "sm" | "md";
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit";
}) {
  const base: CSSProperties = {
    borderRadius: "7px",
    fontWeight: 600,
    cursor: disabled ? "default" : "pointer",
    opacity: disabled ? 0.55 : 1,
    padding: size === "sm" ? "0.3rem 0.65rem" : "0.55rem 1rem",
    fontSize: size === "sm" ? "0.78rem" : "0.88rem",
    border: "1px solid transparent",
    transition: "filter 0.12s ease",
  };
  const variants: Record<ButtonVariant, CSSProperties> = {
    primary: { background: colors.accent, color: "#fff" },
    secondary: { background: colors.surfaceRaised, color: colors.text, border: `1px solid ${colors.borderStrong}` },
    danger: { background: colors.danger, color: "#1a0d0d" },
    ghost: { background: "transparent", color: colors.textMuted, border: `1px solid ${colors.border}` },
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={{ ...base, ...variants[variant] }}
      onMouseEnter={(e) => !disabled && (e.currentTarget.style.filter = "brightness(1.1)")}
      onMouseLeave={(e) => (e.currentTarget.style.filter = "none")}
    >
      {children}
    </button>
  );
}

export const inputStyle: CSSProperties = {
  padding: "0.5rem 0.65rem",
  borderRadius: "7px",
  border: `1px solid ${colors.borderStrong}`,
  background: colors.bg,
  color: colors.text,
  fontSize: "0.88rem",
};

// ---------------------------------------------------------------------------
// State helpers
// ---------------------------------------------------------------------------

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        color: colors.textMuted,
        fontSize: "0.88rem",
        padding: "1.25rem",
        textAlign: "center",
        border: `1px dashed ${colors.border}`,
        borderRadius: "8px",
      }}
    >
      {children}
    </div>
  );
}

export function Skeleton({ height = "1.2rem", width = "100%" }: { height?: string; width?: string }) {
  return (
    <div
      style={{
        height,
        width,
        borderRadius: "6px",
        background: `linear-gradient(90deg, ${colors.surfaceRaised} 25%, ${colors.border} 50%, ${colors.surfaceRaised} 75%)`,
        backgroundSize: "200% 100%",
        animation: "dl-shimmer 1.4s ease-in-out infinite",
      }}
    />
  );
}

export function Banner({ tone, title, children }: { tone: Tone; title: string; children?: ReactNode }) {
  const { fg } = toneColors(tone);
  return (
    <Card tone={tone}>
      <strong style={{ color: fg }}>{title}</strong>
      {children && <div style={{ marginTop: "0.35rem" }}>{children}</div>}
    </Card>
  );
}

// Table style helpers (kept as plain style objects, not a generic <Table>,
// since column shapes differ enough per page that a wrapper component would
// just be indirection).
export const thStyle: CSSProperties = {
  textAlign: "left",
  color: colors.textMuted,
  fontSize: "0.72rem",
  fontWeight: 600,
  letterSpacing: "0.03em",
  textTransform: "uppercase",
  padding: "0 0.6rem 0.5rem 0",
};

export const tdStyle: CSSProperties = {
  padding: "0.5rem 0.6rem 0.5rem 0",
  fontSize: "0.85rem",
};

export const trStyle: CSSProperties = { borderTop: `1px solid ${colors.border}` };
