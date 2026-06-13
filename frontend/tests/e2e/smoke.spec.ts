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
  await page.getByRole("button", { name: "显示事件原文" }).click();
  await expect(page.locator("h1", { hasText: "Cross-border incident draws conflicting casualty reports" })).toBeVisible();
  await page.getByRole("button", { name: "显示事件中文" }).click();
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
  await expect(page.getByText("安全事件").first()).toBeVisible();
  await expect(page.getByText("官方不确定性").first()).toBeVisible();
  await expect(page.getByText("强烈归责").first()).toBeVisible();
  await expect(page.getByText("原文语言：英文").first()).toBeVisible();
  await expect(page.getByText("路透社 / Reuters").first()).toBeVisible();
  await expect(page.getByText(/英国 \/ 欧洲 \/ 原文语言：英文/)).toBeVisible();
  await expect(page.getByText("原文报道")).toBeVisible();
  await expect(page.getByText("翻译失败：翻译服务没有返回可用的中文。")).toBeVisible();
  await expect(page.getByRole("button", { name: "查看对应报道：夜间发生事件，当地应急力量随后介入。" })).toBeVisible();
  await page.getByRole("banner").getByRole("textbox", { name: "搜索事件" }).fill("Cross-border");
  if ((page.viewportSize()?.width ?? 0) >= 1280) {
    await expect(page.getByLabel("事件列表").getByText(/1 条事件/)).toBeVisible();
  } else {
    await expect(page.getByText("1 条匹配结果")).toBeVisible();
  }
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

test("shows actionable empty state when no events exist", async ({ page }) => {
  await page.route("**/api/v1/events**", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: { data: [] } });
    }
    return route.fallback();
  });
  await page.route("**/api/v1/tasks", (route) => route.fulfill({ json: { data: { history: [], queue_depth: null } } }));

  await page.goto("/");

  await expect(page.getByText("暂无事件").last()).toBeVisible();
  await expect(page.getByText(/先点击“采集全部来源”/).last()).toBeVisible();
  await expect(page.getByText("请选择一个事件查看本站分析和来源报道。")).toBeVisible();
});

test("localizes unknown operation task codes", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/tasks", (route) =>
    route.fulfill({
      json: {
        data: {
          history: [
            {
              task_id: "4374af6d-65e3-4259-8db4-e3e7fb24ff7a",
              step: "app.tasks.internal.unmapped_internal_step",
              status: "retrying_internal_state",
              updated_at: new Date().toISOString(),
            },
          ],
          queue_depth: 1,
        },
      },
    })
  );

  await page.goto("/");

  await expect(page.getByText("其他后台任务")).toHaveCount(2);
  await expect(page.getByText("未知状态")).toHaveCount(2);
  await expect(page.getByText("unmapped_internal_step")).toHaveCount(0);
  await expect(page.getByText("retrying_internal_state")).toHaveCount(0);
  await expect(page.getByText("4374af6d-65e3-4259-8db4-e3e7fb24ff7a")).toHaveCount(0);
});
