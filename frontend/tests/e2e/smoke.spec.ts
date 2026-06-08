import { expect, test } from "@playwright/test";

test("renders TruthPuzzle dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("TruthPuzzle")).toBeVisible();
  await expect(page.locator("h1", { hasText: "Cross-border incident draws conflicting casualty reports" })).toBeVisible();
  const eventCard = page.getByRole("button", { name: /Cross-border incident draws/ });
  if ((page.viewportSize()?.width ?? 0) >= 1280) {
    await expect(eventCard.getByText(/3 reports|3 报道/)).toBeVisible();
    await expect(eventCard.getByText(/2 languages|2 语言/)).toBeVisible();
  }
  await expect(page.getByText(/Translate|翻译/)).toBeVisible();
  const categoryFilter = page.getByRole("combobox").filter({ hasText: /All categories|全部分类/ });
  if (await categoryFilter.isVisible()) {
    await expect(categoryFilter).toBeVisible();
    await categoryFilter.selectOption("conflict");
  }
  const analysisToggle = page.getByRole("button", { name: /Analysis|分析/ });
  if (await analysisToggle.isVisible()) {
    await analysisToggle.click();
  }
  await expect(page.getByRole("button", { name: /Re-analyze/ })).toBeVisible();
  await expect(page.getByText(/v1 ·/)).toBeVisible();
  await expect(page.getByText(/Consensus|共识区/)).toBeVisible();
});

test("links a consensus fact to the source article", async ({ page }) => {
  await page.goto("/");
  const analysisToggle = page.getByRole("button", { name: /Analysis|分析/ });
  if (await analysisToggle.isVisible()) {
    await analysisToggle.click();
  }
  await page.getByRole("button", { name: /An overnight incident/ }).click();
  await expect(page.getByText("Officials report 12 casualties after overnight strike")).toBeVisible();
  await expect(page.getByRole("article").locator("p.border-civic", { hasText: "An overnight incident occurred" })).toBeVisible();
  await page.getByRole("button", { name: /Region|地区/ }).click();
  await expect(page.locator("span.uppercase", { hasText: /^europe$/ })).toBeVisible();
});

test("exposes event selection and filters on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByLabel("Selected event")).toBeVisible();
  await expect(page.getByLabel("Sort events")).toBeVisible();
  await expect(page.getByLabel("Filter by region")).toBeVisible();
  await expect(page.getByLabel("Filter by category")).toBeVisible();
  await page.getByLabel("Filter by category").selectOption("conflict");
  await expect(page.locator("h1", { hasText: "Cross-border incident draws conflicting casualty reports" })).toBeVisible();
});
