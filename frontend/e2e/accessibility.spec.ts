import { expect, test } from "@playwright/test";
import path from "node:path";

const routes = [
  "/",
  "/predict",
  "/csv",
  "/transactions",
  "/risk",
  "/explainability",
  "/anomalies",
  "/investigations",
  "/system",
];

test("primary screens meet WCAG 2.1 A/AA axe checks on desktop and mobile", async ({ page }) => {
  const axeScript = path.join(process.cwd(), "node_modules", "axe-core", "axe.min.js");
  const audit: Array<{ route: string; width: number; violations: unknown[] }> = [];

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 960 });
    for (const route of routes) {
      await page.goto(route);
      await page.getByRole("main").waitFor();
      if (route === "/predict") await page.getByText("Anonymized PCA components").click();
      await page.addScriptTag({ path: axeScript });
      const violations = await page.evaluate(async () => {
        type AxeReport = {
          run: (
            context: Document,
            options: { runOnly: { type: "tag"; values: string[] } },
          ) => Promise<{
            violations: Array<{
              id: string;
              impact: string | null;
              description: string;
              nodes: Array<{ target: string[]; failureSummary: string | null }>;
            }>;
          }>;
        };
        const axe = (window as Window & { axe?: AxeReport }).axe;
        if (!axe) throw new Error("axe-core failed to load in the browser.");
        const report = await axe.run(document, {
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
          },
        });
        return report.violations.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          description: violation.description,
          nodes: violation.nodes.map((node) => ({
            target: node.target,
            failureSummary: node.failureSummary,
          })),
        }));
      });
      audit.push({ route, width, violations });
    }
  }

  const failures = audit.flatMap((result) =>
    result.violations.length ? [{ ...result, violations: result.violations }] : [],
  );
  if (failures.length) console.log(JSON.stringify(failures, null, 2));
  expect(failures, "axe-core reported WCAG A/AA or best-practice violations").toEqual([]);
});
