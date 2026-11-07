import { FEATURE_COLUMNS, type FeatureName, type FeatureVector } from "@/lib/types";

export type FeatureParseResult =
  | { ok: true; value: FeatureVector }
  | { ok: false; error: string };

export type BatchParseResult =
  | { ok: true; value: FeatureVector[] }
  | { ok: false; error: string };

export function createZeroFeatureTemplate(): FeatureVector {
  return Object.fromEntries(FEATURE_COLUMNS.map((name) => [name, 0])) as FeatureVector;
}

export function validateFeatureVector(value: unknown): FeatureParseResult {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return { ok: false, error: "Enter one JSON object with the 30 required numeric features." };
  }
  const record = value as Record<string, unknown>;
  const expected = new Set<string>(FEATURE_COLUMNS);
  const missing = FEATURE_COLUMNS.filter((name) => !(name in record));
  const extra = Object.keys(record).filter((name) => !expected.has(name));
  if (missing.length || extra.length) {
    const parts = [
      missing.length ? `Missing: ${missing.slice(0, 4).join(", ")}${missing.length > 4 ? "…" : ""}.` : "",
      extra.length ? `Unexpected: ${extra.slice(0, 4).join(", ")}${extra.length > 4 ? "…" : ""}.` : "",
    ].filter(Boolean);
    return { ok: false, error: parts.join(" ") };
  }
  for (const name of FEATURE_COLUMNS) {
    const number = record[name];
    if (typeof number !== "number" || !Number.isFinite(number)) {
      return { ok: false, error: `${name} must be a finite JSON number.` };
    }
  }
  return { ok: true, value: record as FeatureVector };
}

export function parseFeatureInputs(
  values: Partial<Record<FeatureName, string>>,
): FeatureParseResult {
  const parsed: Record<string, number> = {};
  for (const name of FEATURE_COLUMNS) {
    const raw = values[name];
    if (raw === undefined || raw.trim() === "") {
      return { ok: false, error: `${name} is required.` };
    }
    const number = Number(raw);
    if (!Number.isFinite(number)) {
      return { ok: false, error: `${name} must be a finite number.` };
    }
    parsed[name] = number;
  }
  return { ok: true, value: parsed as FeatureVector };
}

export function parseFeatureJson(text: string): FeatureParseResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, error: "The feature vector is not valid JSON." };
  }
  return validateFeatureVector(parsed);
}

export function parseBatchJson(text: string): BatchParseResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { ok: false, error: "The transaction batch is not valid JSON." };
  }
  const rows = Array.isArray(parsed)
    ? parsed
    : typeof parsed === "object" && parsed !== null && Array.isArray((parsed as { transactions?: unknown }).transactions)
      ? (parsed as { transactions: unknown[] }).transactions
      : null;
  if (!rows || rows.length === 0) {
    return { ok: false, error: "Provide a non-empty array of feature vectors (maximum 1,000)." };
  }
  if (rows.length > 1000) return { ok: false, error: "A batch can contain at most 1,000 rows." };
  for (let index = 0; index < rows.length; index += 1) {
    const result = validateFeatureVector(rows[index]);
    if (!result.ok) return { ok: false, error: `Row ${index + 1}: ${result.error}` };
  }
  return { ok: true, value: rows as FeatureVector[] };
}

export function featureTemplateText(): string {
  return JSON.stringify(createZeroFeatureTemplate(), null, 2);
}

export function isFeatureName(value: string): value is FeatureName {
  return (FEATURE_COLUMNS as readonly string[]).includes(value);
}
