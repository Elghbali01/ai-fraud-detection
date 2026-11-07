import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const features: Record<string, number> = {
  Time: 0,
  ...Object.fromEntries(Array.from({ length: 28 }, (_, index) => [`V${index + 1}`, 0])),
  Amount: 0,
};

test.describe("local analyst workflows", () => {
  test("connects to the API and keeps mobile navigation within the viewport", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("API connected")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Model ready")).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
    expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.width + 1);
    await page.getByRole("button", { name: "Open navigation" }).click();
    await expect(page.getByRole("navigation", { name: "Workspace" })).toBeVisible();
    await page
      .getByRole("navigation", { name: "Workspace" })
      .getByRole("link", { name: "Prediction lab", exact: true })
      .click();
    await expect(page.getByRole("heading", { name: "Prediction lab" })).toBeVisible();
  });

  test("scores one explicitly synthetic vector and requests a local explanation", async ({ page }) => {
    await page.goto("/predict");
    await page.getByRole("button", { name: "Insert zero-filled template" }).click();
    await page.getByRole("button", { name: "Score transaction" }).click();
    await expect(page.getByRole("heading", { name: "Prediction result" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Persisted record")).toBeVisible();
    await page.getByRole("button", { name: "Explain this vector" }).click();
    await expect(page.getByRole("heading", { name: "Local explanation · raw log-odds" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("All 30 feature contributions are shown.")).toBeVisible();
    await expect(page.getByRole("figure", { name: "Cumulative raw log-odds waterfall" })).toBeVisible();
  });

  test("scores a bounded batch through the prediction endpoint", async ({ page }) => {
    await page.goto("/predict");
    await page.getByRole("tab", { name: "Batch scoring" }).click();
    await page.getByLabel("Batch feature vectors JSON").fill(JSON.stringify([features, features]));
    await page.getByRole("button", { name: "Score batch" }).click();
    await expect(page.getByRole("heading", { name: "Batch results" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("2 persisted predictions")).toBeVisible();
    const resultRows = page.locator(".table-wrap table tbody tr");
    const tier = (await resultRows.first().locator("td").nth(4).innerText()).trim();
    await page.getByLabel("Filter batch by risk tier").selectOption(tier);
    await expect(resultRows).toHaveCount(2);
    await page.getByLabel("Sort batch results").selectOption("risk_desc");
    await expect(page.getByLabel("Sort batch results")).toHaveValue("risk_desc");
  });

  test("uploads a synthetic one-row CSV, reviews results, and deletes the analysis", async ({ page }) => {
    await page.goto("/csv");
    const columns = ["Time", ...Array.from({ length: 28 }, (_, index) => `V${index + 1}`), "Amount"];
    const csv = `${columns.join(",")}\n${columns.map(() => "0").join(",")}\n`;
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download CSV header template" }).click();
    const templateDownload = await downloadPromise;
    expect(templateDownload.suggestedFilename()).toBe("fraud-feature-template.csv");
    const templatePath = await templateDownload.path();
    if (templatePath) expect(await readFile(templatePath, "utf8")).toBe(`${columns.join(",")}\n`);
    const dataTransfer = await page.evaluateHandle((content) => {
      const transfer = new DataTransfer();
      transfer.items.add(new File([content], "mission05-e2e-synthetic.csv", { type: "text/csv" }));
      return transfer;
    }, csv);
    await page.locator(".file-drop").dispatchEvent("drop", { dataTransfer });
    await expect(page.locator(".file-drop strong")).toHaveText("mission05-e2e-synthetic.csv");
    await page.getByRole("button", { name: "Upload and validate" }).click();
    await expect(page.getByText("Validated rows")).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Create analysis" }).click();
    await expect(page.getByRole("heading", { name: "Analysis results" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByRole("heading", { name: "Paginated results" })).toBeVisible();
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Delete analysis and results" }).click();
    await expect(page).toHaveURL(/\/csv$/);
  });

  test("runs explicit bounded risk and separate anomaly requests", async ({ page }) => {
    await page.goto("/risk");
    await expect(page.getByText("Persisted risk policy")).toBeVisible();
    await page.getByRole("button", { name: "Insert synthetic vector" }).click();
    await page.getByRole("button", { name: "Prioritize transactions" }).click();
    await expect(page.getByRole("heading", { name: "Prioritized review queue" })).toBeVisible({ timeout: 60_000 });
    await page.goto("/anomalies");
    await page.getByRole("button", { name: "Insert explicit zero vector" }).click();
    await page.getByRole("button", { name: "Score anomaly signal" }).click();
    await expect(page.getByRole("heading", { name: "Anomaly results" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Not a probability").first()).toBeVisible();
  });

  test("creates a clearly labeled synthetic case, records a transition, and appends a note", async ({ page }) => {
    await page.goto("/investigations");
    await page.getByLabel("Case title").fill("Mission 05 E2E synthetic review");
    await page.getByLabel("Reason").fill("Automated browser integration check using an explicit zero feature vector.");
    await page.getByRole("button", { name: "Create investigation" }).click();
    await expect(page.getByRole("heading", { name: "Investigation details" })).toBeVisible({ timeout: 30_000 });
    await page.getByLabel("Next status").selectOption("In Review");
    await page.getByLabel("Record analyst outcome").selectOption("Unconfirmed");
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("In Review").first()).toBeVisible({ timeout: 30_000 });
    await page.getByLabel("Append a note").fill("Synthetic E2E note; not a fraud finding.");
    await page.getByRole("button", { name: "Add note" }).click();
    await expect(page.getByText("Synthetic E2E note; not a fraud finding.")).toBeVisible({ timeout: 30_000 });
  });

  test("renders global validation-time explainability without claiming probability additivity", async ({ page }) => {
    await page.goto("/explainability");
    await expect(page.getByText("Global SHAP baseline")).toBeVisible();
    await expect(page.getByText("VALIDATION PARTITION")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/not direct additions to the later calibrated fraud probability/i)).toBeVisible();
    await page.getByLabel("Explanation feature vector JSON").fill(JSON.stringify(features));
    await page.getByRole("button", { name: "Explain supplied vector" }).click();
    await expect(page.getByRole("figure", { name: "Cumulative raw log-odds waterfall" })).toBeVisible({ timeout: 60_000 });
  });
});
