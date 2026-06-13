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
  const sourceGraph = page.getByLabel("来源图谱");
  await expect(sourceGraph.getByText("路透社 / Reuters")).toBeVisible();
  await expect(sourceGraph.getByText("伊朗伊斯兰共和国通讯社 / IRNA")).toBeVisible();
  await expect(page.getByText("原文语言：英文").first()).toBeVisible();
  await expect(page.getByText("路透社 / Reuters").first()).toBeVisible();
  await expect(page.getByText(/英国 \/ 欧洲 \/ 原文语言：英文/)).toBeVisible();
  await expect(page.getByText("中文翻译")).toBeVisible();
  await expect(page.getByText("自动翻译接口暂不可用：当前显示已保存的中文译文，可点击“显示原文”查看来源原文。")).toBeVisible();
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
  await expect(page.getByText("官员称夜间袭击造成 12 人死亡")).toBeVisible();
  await page.getByRole("article").getByRole("button", { name: "显示原文" }).click();
  await expect(page.getByText("Officials report 12 casualties after overnight strike")).toBeVisible();
  await expect(page.getByText("选中的事实片段")).toBeVisible();
  if ((page.viewportSize()?.width ?? 0) >= 768) {
    await page.getByRole("button", { name: "地区", exact: true }).click();
    await expect(page.locator("span").filter({ hasText: /^欧洲$/ })).toBeVisible();
  }
});

test("queues the event pipeline from the reanalyze button", async ({ page }) => {
  await useDemoData(page);
  let queued = false;
  await page.route("**/api/v1/events/demo/pipeline", (route) => {
    queued = true;
    return route.fulfill({ json: { data: { task_id: "task-1", event_id: "demo", status: "queued" } } });
  });

  await page.goto("/");

  await page.getByRole("button", { name: "重新分析" }).click();
  await expect(page.getByText("已加入后台分析队列，完成后页面会自动更新。")).toBeVisible();
  expect(queued).toBeTruthy();
});

test("refreshes analysis after a live analysis update", async ({ page }) => {
  await page.addInitScript(() => {
    const sockets: Array<{ onmessage?: (event: { data: string }) => void; onopen?: (event: Event) => void }> = [];
    (window as unknown as { __mockSockets: typeof sockets }).__mockSockets = sockets;
    (window as unknown as { __sendAnalysisUpdated: () => void }).__sendAnalysisUpdated = () => {
      for (const socket of sockets) {
        socket.onmessage?.({ data: JSON.stringify({ type: "analysis_updated", event_id: "evt-1" }) });
      }
    };
    class MockWebSocket {
      onclose?: (event: Event) => void;
      onerror?: (event: Event) => void;
      onmessage?: (event: { data: string }) => void;
      onopen?: (event: Event) => void;
      readyState = 0;
      url: string;

      constructor(url: string) {
        this.url = url;
        sockets.push(this);
        window.setTimeout(() => {
          this.readyState = 1;
          this.onopen?.(new Event("open"));
        }, 0);
      }

      close() {
        this.readyState = 3;
        this.onclose?.(new Event("close"));
      }

      send() {}
    }
    (window as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
  });
  let analysisCalls = 0;
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      return route.fulfill({
        json: {
          data: [{
            id: "evt-1",
            title: "测试事件",
            summary: "用于验证实时更新。",
            category: "conflict",
            region_primary: "europe",
            status: "active",
            article_count: 1,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 50,
            last_updated_at: new Date().toISOString(),
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-1/articles") {
      return route.fulfill({ json: { data: [] } });
    }
    if (url.pathname === "/api/v1/events/evt-1/analysis") {
      analysisCalls += 1;
      return route.fulfill({
        json: {
          data: {
            event_id: "evt-1",
            summary: analysisCalls === 1 ? "旧分析摘要" : "新分析摘要",
            analysis_version: analysisCalls,
            article_count_at_analysis: 1,
            consensus_facts: [],
            disputed_facts: [],
            blind_spots: [],
            narrative_frames: [],
            source_graph: { nodes: [], edges: [] },
            timeline: [],
          },
        },
      });
    }
    if (url.pathname === "/api/v1/tasks") {
      return route.fulfill({ json: { data: { history: [], queue_depth: null } } });
    }
    return route.abort();
  });

  await page.goto("/");

  await expect(page.getByText("旧分析摘要")).toBeVisible();
  await page.waitForFunction(() => (window as unknown as { __mockSockets?: unknown[] }).__mockSockets?.length);
  await page.evaluate(() => (window as unknown as { __sendAnalysisUpdated: () => void }).__sendAnalysisUpdated());
  await expect(page.getByText("实时更新 · 本站分析已更新")).toBeVisible();
  await expect(page.getByText("新分析摘要")).toBeVisible();
  expect(analysisCalls).toBeGreaterThanOrEqual(2);
});

test("exposes event selection and filters on mobile", async ({ page }) => {
  await useDemoData(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await expect(page.getByLabel("选择事件")).toBeVisible();
  await expect(page.locator("select[aria-label='事件排序']").last()).toBeVisible();
  await expect(page.locator("select[aria-label='按地区筛选']").last()).toBeVisible();
  await expect(page.locator("select[aria-label='按分类筛选']").last()).toBeVisible();
  await page.locator("select[aria-label='按分类筛选']").last().selectOption("conflict");
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

test("clears stale reports when filters remove all events", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/events**", (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.get("category") === "technology") {
      return route.fulfill({ json: { data: [] } });
    }
    return route.abort();
  });

  await page.goto("/");

  await expect(page.getByText("官员称夜间袭击造成 12 人死亡")).toBeVisible();
  await page.locator("select[aria-label='按分类筛选']").last().selectOption("technology");
  await expect(page.getByText("请选择一个事件查看本站分析和来源报道。")).toBeVisible();
  await expect(page.getByText("官员称夜间袭击造成 12 人死亡")).toHaveCount(0);
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
