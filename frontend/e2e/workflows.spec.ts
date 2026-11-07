import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const features: Record<string, number> = {
  Time: 0,
  ...Object.fromEntries(Array.from({ length: 28 }, (_, index) => [`V${index + 1}`, 0])),
  Amount: 0,
};

const apiBaseURL = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

test.describe("local analyst workflows", () => {
  test("connects to the API and keeps mobile navigation within the viewport", async ({ page }) => {
    const response = await page.goto("/");
    const headers = response?.headers() ?? {};
    expect(headers["content-security-policy"]).toContain("nonce-");
    expect(headers["content-security-policy"]).toContain(`connect-src 'self' ${new URL(apiBaseURL).origin}`);
    expect(headers["content-security-policy"]).not.toContain("script-src 'self' 'unsafe-inline'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
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

  test("rejects an incomplete prediction without showing a result", async ({ page }) => {
    await page.goto("/predict");
    await page.getByLabel("Time", { exact: true }).fill("12");
    await page.getByRole("button", { name: "Score transaction" }).click();
    await expect(page.locator(".form-error[role='alert']")).toContainText(/required/i);
    await expect(page.getByRole("heading", { name: "Prediction result" })).toHaveCount(0);
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

  test("uploads a synthetic ten-row CSV, reviews results, and deletes the analysis", async ({ page }) => {
    await page.goto("/csv");
    const columns = ["Time", ...Array.from({ length: 28 }, (_, index) => `V${index + 1}`), "Amount"];
    const csvRows = Array.from({ length: 10 }, (_, index) =>
      columns.map((column) => (column === "Time" ? String(index * 600) : "0")).join(","),
    );
    const csv = `${columns.join(",")}\n${csvRows.join("\n")}\n`;
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
    await expect(page.locator(".kv").filter({ hasText: "Rows processed" }).locator(".kv-value")).toHaveText("10");
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Delete analysis and results" }).click();
    await expect(page).toHaveURL(/\/csv$/);
  });

  test("rejects a malformed feature CSV safely", async ({ page }) => {
    await page.goto("/csv");
    const invalidCsv = "Time,V1,Class\n0,0,1\n";
    await page.getByLabel("Choose feature-only CSV").setInputFiles({
      name: "invalid-synthetic.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(invalidCsv),
    });
    await page.getByRole("button", { name: "Upload and validate" }).click();
    await expect(page.locator(".form-error[role='alert']")).toContainText(/column|feature|class|schema/i, { timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Create analysis" })).toHaveCount(0);
  });

  test("runs explicit bounded risk and separate anomaly requests", async ({ page }) => {
    await page.goto("/risk");
    await expect(page.getByText("Persisted risk policy")).toBeVisible();
    await page.getByLabel("Transactions for prioritization").fill(JSON.stringify([features, features, features]));
    await page.getByLabel("Maximum alerts").fill("2");
    await page.getByLabel("Low").check();
    await page.getByRole("button", { name: "Prioritize transactions" }).click();
    await expect(page.getByRole("heading", { name: "Prioritized review queue" })).toBeVisible({ timeout: 60_000 });
    let rankedRows = page.locator(".table-wrap table tbody tr");
    await expect(rankedRows).toHaveCount(2);
    await expect(rankedRows.nth(0).locator("td").nth(1)).toHaveText("1");
    await expect(rankedRows.nth(1).locator("td").nth(1)).toHaveText("2");
    await page.getByRole("tab", { name: "Percentage budget" }).click();
    await page.getByLabel("Review budget (%)").fill("50");
    await page.getByRole("button", { name: "Prioritize transactions" }).click();
    rankedRows = page.locator(".table-wrap table tbody tr");
    await expect(rankedRows).toHaveCount(2);
    await expect(page.getByText("50% · backend ceiling")).toBeVisible();
    await page.goto("/anomalies");
    await page.getByRole("button", { name: "Insert explicit zero vector" }).click();
    await page.getByRole("button", { name: "Score anomaly signal" }).click();
    await expect(page.getByRole("heading", { name: "Anomaly results" })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Not a probability").first()).toBeVisible();
  });

  test("creates a clearly labeled synthetic case, records a transition, and appends a note", async ({ page }) => {
    await page.goto("/investigations");
    await page.getByLabel("Case title").fill("Mission 06 E2E synthetic review");
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
    await page.reload();
    await page.getByRole("button", { name: "Open case" }).first().click();
    await expect(page.getByRole("heading", { name: "Investigation details" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Synthetic E2E note; not a fraud finding.")).toBeVisible();
    await expect(page.getByText("In Review").first()).toBeVisible();
    await expect(page.getByText(/Analyst outcome recorded: Yes · adjudicated ground truth: Not provided\./)).toBeVisible();
  });

  test("renders global validation-time explainability without claiming probability additivity", async ({ page }) => {
    await page.goto("/explainability");
    await expect(page.getByText("Global SHAP baseline")).toBeVisible();
    await expect(page.getByText("VALIDATION PARTITION", { exact: true })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/not direct additions to the later calibrated fraud probability/i)).toBeVisible();
    await page.getByLabel("Explanation feature vector JSON").fill(JSON.stringify(features));
    await page.getByRole("button", { name: "Explain supplied vector" }).click();
    await expect(page.getByRole("figure", { name: "Cumulative raw log-odds waterfall" })).toBeVisible({ timeout: 60_000 });
  });

  test("filters and paginates synthetic prediction history", async ({ page, request }) => {
    const initialHistory = await request.get(`${apiBaseURL}/history?limit=1&offset=0`);
    expect(initialHistory.ok()).toBeTruthy();
    const existingCount = Number((await initialHistory.json()).total);
    for (let index = 0; index < 30; index += 1) {
      const response = await request.post(`${apiBaseURL}/predictions`, { data: features });
      expect(response.ok()).toBeTruthy();
    }
    const expectedTotal = existingCount + 30;
    const formattedTotal = expectedTotal.toLocaleString("en-US");
    await page.goto("/transactions");
    await expect(page.getByText(`Rows 1–25 of ${formattedTotal}`)).toBeVisible({ timeout: 30_000 });
    const next = page.getByRole("button", { name: "Next" });
    await expect(next).toBeEnabled();
    await next.click();
    const secondPageEnd = Math.min(50, expectedTotal).toLocaleString("en-US");
    await expect(page.getByText(`Rows 26–${secondPageEnd} of ${formattedTotal}`)).toBeVisible();
    await page.getByRole("button", { name: "Previous" }).click();
    const firstTier = (await page.locator(".table-wrap table tbody tr").first().locator("td").nth(5).innerText()).trim();
    await page.getByLabel("Risk tier").selectOption(firstTier);
    await expect(page.locator(".table-wrap table tbody tr")).toHaveCount(25);
    await page.getByLabel("Model version").fill("no-such-model-version");
    await expect(page.getByText("No matching records")).toBeVisible();
    await page.getByLabel("Model version").fill("");
    await expect(page.locator(".table-wrap table tbody tr")).toHaveCount(25);
  });

  test("recovers from an API network interruption", async ({ page }) => {
    await page.route("**/api/v1/**", (route) => route.abort());
    await page.goto("/system");
    await expect(page.getByText("API offline", { exact: true })).toBeVisible({ timeout: 30_000 });
    await page.unroute("**/api/v1/**");
    await page.reload();
    await expect(page.getByText("API connected", { exact: true })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Model ready", { exact: true })).toBeVisible({ timeout: 30_000 });
  });

  test("keeps every primary route within four responsive viewports", async ({ page }) => {
    const routes = ["/", "/predict", "/csv", "/transactions", "/risk", "/explainability", "/anomalies", "/investigations", "/system"];
    const failures: Array<{ route: string; width: number; pageWidth: number; contentWidth: number }> = [];
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 960 });
      for (const route of routes) {
        await page.goto(route);
        await page.getByRole("main").waitFor();
        const dimensions = await page.evaluate(() => ({
          pageWidth: document.documentElement.clientWidth,
          contentWidth: document.documentElement.scrollWidth,
        }));
        if (dimensions.contentWidth > dimensions.pageWidth + 1) failures.push({ route, width, ...dimensions });
      }
    }
    expect(failures).toEqual([]);
  });

  test("supports keyboard access to the skip link and workspace navigation", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    await expect(page.locator(".skip-link")).toBeFocused();
    const outlineStyle = await page.locator(".skip-link").evaluate((element) => getComputedStyle(element).outlineStyle);
    expect(outlineStyle).not.toBe("none");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("main")).toBeFocused();
  });
});
