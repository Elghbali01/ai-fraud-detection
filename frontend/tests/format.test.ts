import { describe, expect, it } from "vitest";
import { formatDate, formatProbability, percentWidth, riskTone } from "@/lib/format";

describe("display helpers", () => {
  it("formats model probabilities without conflating scores", () => {
    expect(formatProbability(0.183592)).toBe("18.36%");
    expect(formatProbability(null)).toBe("—");
  });

  it("clamps bar widths and maps risk tiers to labeled styles", () => {
    expect(percentWidth(12, 10)).toBe(100);
    expect(percentWidth(-1, 10)).toBe(0);
    expect(riskTone("Critical")).toBe("tone-critical");
    expect(riskTone("unknown")).toBe("tone-neutral");
  });

  it("handles invalid timestamps explicitly", () => {
    expect(formatDate("not-a-date")).toBe("—");
  });
});
