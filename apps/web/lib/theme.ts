/**
 * Plain design tokens and formatters -- no "use client" directive, so
 * server components (like app/layout.tsx) can import these directly.
 * Anything that renders JSX or uses client-only APIs lives in ui.tsx
 * instead, which re-exports everything from here for convenience.
 */

export const colors = {
  bg: "#0a0d13",
  surface: "#11151d",
  surfaceRaised: "#161b26",
  border: "#1f2430",
  borderStrong: "#2a3142",
  text: "#e8eaef",
  textMuted: "#8b93a4",
  textFaint: "#5b6375",
  accent: "#5b84ff",
  accentSoft: "rgba(91, 132, 255, 0.14)",
  success: "#3ecf8e",
  successSoft: "rgba(62, 207, 142, 0.14)",
  warning: "#e3a83b",
  warningSoft: "rgba(227, 168, 59, 0.14)",
  danger: "#ff6b6b",
  dangerSoft: "rgba(255, 107, 107, 0.14)",
  neutral: "#8b93a4",
  neutralSoft: "rgba(139, 147, 164, 0.14)",
} as const;

export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export function toneColors(tone: Tone): { fg: string; bg: string } {
  switch (tone) {
    case "success":
      return { fg: colors.success, bg: colors.successSoft };
    case "warning":
      return { fg: colors.warning, bg: colors.warningSoft };
    case "danger":
      return { fg: colors.danger, bg: colors.dangerSoft };
    case "info":
      return { fg: colors.accent, bg: colors.accentSoft };
    default:
      return { fg: colors.neutral, bg: colors.neutralSoft };
  }
}

/** Score bands used consistently for the 0-100 screening score and the PE
 * attractiveness read-out -- green means "keep going", amber means "check
 * the assumptions", red means "this is likely a pass". */
export function scoreTone(score: number): Tone {
  if (score >= 70) return "success";
  if (score >= 45) return "warning";
  return "danger";
}

export function recommendationTone(rec: string): Tone {
  if (rec === "PROCEED_TO_DD") return "success";
  if (rec === "HOLD") return "warning";
  return "danger";
}

export function sourceTone(source: string): Tone {
  if (source === "computed") return "success";
  if (source === "assumption") return "info";
  if (source === "default") return "warning";
  return "neutral";
}

export function peerStatusTone(status: string): Tone {
  if (status === "SELECTED") return "success";
  if (status === "REJECTED") return "danger";
  return "warning";
}

export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}bn`;
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}m`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "–";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatMultiple(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "–";
  return `${value.toFixed(digits)}x`;
}
