import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

async function useDemoData(page: Page) {
  await page.route("**/api/v1/**", (route) => route.abort());
}

test("renders TruthPuzzle dashboard", async ({ page }) => {
  await useDemoData(page);
  await page.goto("/");
  await expect(page.getByText("TruthPuzzle")).toBeVisible();
  await expect(page.locator("h1", { hasText: "边境事件出现相互矛盾的伤亡报道" })).toBeVisible();
  const eventCard = page.getByRole("button", { name: /边境事件出现/ });
  if ((page.viewportSize()?.width ?? 0) >= 1280) {
    await expect(eventCard.getByText(/3 报道/)).toBeVisible();
    await expect(eventCard.getByText(/2 语言/)).toBeVisible();
  }
  await expect(page.getByRole("article").getByRole("button", { name: /显示原文|显示中文/ })).toBeVisible();
  const categoryFilter = page.getByRole("combobox").filter({ hasText: /All categories|全部分类/ });
  if (await categoryFilter.isVisible()) {
    await expect(categoryFilter).toBeVisible();
    await categoryFilter.selectOption("conflict");
  }
  await expect(page.getByRole("button", { name: /重新分析/ })).toBeVisible();
  await expect(page.getByText("队列 未知")).toHaveCount(2);
  await expect(page.getByText("队列 n/a")).toHaveCount(0);
  await expect(page.getByText(/v1 ·/)).toBeVisible();
  await expect(page.getByText(/共识区/)).toBeVisible();
  await expect(page.getByText("含 1 篇通讯社转载")).toBeVisible();
  await expect(page.getByText("原文语言：英文").first()).toBeVisible();
  await expect(page.getByText("路透社 / Reuters").first()).toBeVisible();
  await expect(page.getByText(/英国 \/ 欧洲 \/ 原文语言：英文/)).toBeVisible();
  await expect(page.getByRole("button", { name: "查看对应报道：夜间发生事件，当地应急力量随后介入。" })).toBeVisible();
});

test("links a consensus fact to the source article", async ({ page }) => {
  await useDemoData(page);
  await page.goto("/");
  await page.getByRole("button", { name: /夜间发生事件/ }).click();
  await expect(page.getByText("Officials report 12 casualties after overnight strike")).toBeVisible();
  await expect(page.getByText("选中的事实片段")).toBeVisible();
  if ((page.viewportSize()?.width ?? 0) >= 768) {
    await page.getByRole("button", { name: "地区", exact: true }).click();
    await expect(page.locator("span").filter({ hasText: /^欧洲$/ })).toBeVisible();
  }
});

test("exposes event selection and filters on mobile", async ({ page }) => {
  await useDemoData(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByLabel("选择事件")).toBeVisible();
  await expect(page.getByLabel("事件排序")).toBeVisible();
  await expect(page.getByLabel("按地区筛选")).toBeVisible();
  await expect(page.getByLabel("按分类筛选")).toBeVisible();
  await page.getByLabel("按分类筛选").selectOption("conflict");
  await expect(page.locator("h1", { hasText: "边境事件出现相互矛盾的伤亡报道" })).toBeVisible();
});
