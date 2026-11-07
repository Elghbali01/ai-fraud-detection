import type { RiskTier } from "@/lib/types";

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value);
}

export function formatProbability(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "—";
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date) + " UTC";
}

export function compactId(value: string | null | undefined): string {
  if (!value) return "—";
  return `${value.slice(0, 8)}…${value.slice(-4)}`;
}

export function riskTone(tier: RiskTier | string): string {
  return {
    Low: "tone-low",
    Elevated: "tone-elevated",
    High: "tone-high",
    Critical: "tone-critical",
  }[tier] ?? "tone-neutral";
}

export function percentWidth(value: number, maximum: number): number {
  if (!Number.isFinite(value) || !Number.isFinite(maximum) || maximum <= 0) return 0;
  return Math.min(100, Math.max(0, (value / maximum) * 100));
}

export { numberFormat };
