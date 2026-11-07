import type { Prediction, RiskTier } from "@/lib/types";

export type BatchSort = "input" | "probability_desc" | "probability_asc" | "risk_desc";

type BatchResult = Pick<Prediction, "risk_tier" | "fraud_probability" | "risk_score">;

export function filterAndSortBatch<T extends BatchResult>(
  rows: readonly T[],
  tier: "" | RiskTier,
  sort: BatchSort,
): T[] {
  return rows
    .filter((row) => !tier || row.risk_tier === tier)
    .slice()
    .sort((left, right) => {
      if (sort === "probability_desc") return right.fraud_probability - left.fraud_probability;
      if (sort === "probability_asc") return left.fraud_probability - right.fraud_probability;
      if (sort === "risk_desc") return right.risk_score - left.risk_score;
      return 0;
    });
}
