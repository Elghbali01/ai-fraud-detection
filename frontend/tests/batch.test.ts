import { describe, expect, it } from "vitest";
import { filterAndSortBatch } from "@/lib/batch";

describe("bounded batch result controls", () => {
  const rows = [
    { record_id: "low", risk_tier: "Low" as const, fraud_probability: 0.2, risk_score: 20 },
    { record_id: "critical", risk_tier: "Critical" as const, fraud_probability: 0.9, risk_score: 90 },
    { record_id: "high", risk_tier: "High" as const, fraud_probability: 0.5, risk_score: 50 },
  ];

  it("sorts by either returned probability or score without mutating the input", () => {
    expect(filterAndSortBatch(rows, "", "probability_desc").map((row) => row.record_id)).toEqual([
      "critical",
      "high",
      "low",
    ]);
    expect(filterAndSortBatch(rows, "", "probability_asc").map((row) => row.record_id)).toEqual([
      "low",
      "high",
      "critical",
    ]);
    expect(filterAndSortBatch(rows, "", "risk_desc").map((row) => row.record_id)).toEqual([
      "critical",
      "high",
      "low",
    ]);
    expect(rows.map((row) => row.record_id)).toEqual(["low", "critical", "high"]);
  });

  it("filters by the API-returned operational tier", () => {
    expect(filterAndSortBatch(rows, "High", "input").map((row) => row.record_id)).toEqual([
      "high",
    ]);
  });
});
