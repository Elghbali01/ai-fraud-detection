import { describe, expect, it } from "vitest";
import {
  createZeroFeatureTemplate,
  parseBatchJson,
  parseFeatureInputs,
  parseFeatureJson,
} from "@/lib/features";
import { FEATURE_COLUMNS } from "@/lib/types";

describe("Mission 04 feature contract", () => {
  it("creates exactly the 30 required numeric fields", () => {
    const template = createZeroFeatureTemplate();
    expect(Object.keys(template)).toEqual(FEATURE_COLUMNS);
    expect(Object.values(template).every((value) => value === 0)).toBe(true);
  });

  it("accepts a finite exact-schema feature vector", () => {
    expect(parseFeatureJson(JSON.stringify(createZeroFeatureTemplate())).ok).toBe(true);
  });

  it("parses all 30 guided numeric inputs and reports missing or invalid values", () => {
    const values = Object.fromEntries(FEATURE_COLUMNS.map((name) => [name, "0"]));
    expect(parseFeatureInputs(values).ok).toBe(true);
    expect(parseFeatureInputs({ ...values, V7: "" })).toMatchObject({
      ok: false,
      error: "V7 is required.",
    });
    expect(parseFeatureInputs({ ...values, Amount: "Infinity" })).toMatchObject({
      ok: false,
      error: "Amount must be a finite number.",
    });
  });

  it("rejects Class labels, extra keys, booleans and non-finite numbers", () => {
    const template = createZeroFeatureTemplate() as Record<string, unknown>;
    expect(parseFeatureJson(JSON.stringify({ ...template, Class: 0 })).ok).toBe(false);
    expect(parseFeatureJson(JSON.stringify({ ...template, Amount: true })).ok).toBe(false);
    expect(parseFeatureJson(JSON.stringify({ ...template, V1: "1" })).ok).toBe(false);
    expect(parseFeatureJson("not-json").ok).toBe(false);
  });

  it("validates each batch row and enforces the backend row bound", () => {
    const row = createZeroFeatureTemplate();
    expect(parseBatchJson(JSON.stringify([row, row])).ok).toBe(true);
    expect(parseBatchJson(JSON.stringify([{ ...row, Class: 1 }])).ok).toBe(false);
    expect(parseBatchJson(JSON.stringify([])).ok).toBe(false);
  });
});
