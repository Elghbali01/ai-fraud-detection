import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState, ErrorState, RiskBadge } from "@/components/ui";
import { ShapRows, ShapWaterfall } from "@/components/charts";

describe("risk and explanation labels", () => {
  it("renders a readable tier name in addition to its color treatment", () => {
    render(<RiskBadge tier="Critical" />);
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("shows an explicit empty state and actionable offline error", () => {
    const { rerender } = render(<EmptyState title="No records" description="The API has no data." />);
    expect(screen.getByText("No records")).toBeInTheDocument();
    rerender(<ErrorState error={new Error("Cannot reach the local API.")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("API is unavailable");
  });

  it("labels contribution values and direction in log-odds space", () => {
    render(<ShapRows contributions={[{ feature: "V14", contribution: -0.25 }, { feature: "Amount", contribution: 0.12 }]} />);
    expect(screen.getByText("V14")).toBeInTheDocument();
    expect(screen.getByText("Amount")).toBeInTheDocument();
    expect(screen.getByRole("list")).toHaveAttribute("aria-label", "Feature contributions in raw log-odds space");
  });

  it("shows cumulative waterfall steps and an equivalent accessible data table", () => {
    render(<ShapWaterfall baseValue={-1} outputValue={-1.25} contributions={[
      { feature: "V14", contribution: 0.25 },
      { feature: "Amount", contribution: -0.5 },
    ]} />);
    expect(screen.getByRole("figure", { name: "Cumulative raw log-odds waterfall" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Raw log-odds contribution steps" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Raw log-odds contribution steps" })).toHaveTextContent(/Model output\s*-1\.25 raw log-odds/);
  });
});
