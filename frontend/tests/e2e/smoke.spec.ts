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
    await eventCard.getByRole("button", { name: "显示原文" }).click();
    const originalEventCard = page.getByRole("button", { name: /Cross-border incident draws/ });
    await expect(originalEventCard).toBeVisible();
    await originalEventCard.getByRole("button", { name: "显示中文" }).click();
    await expect(eventCard.getByText("边境事件出现相互矛盾的伤亡报道")).toBeVisible();
  }
  await expect(page.getByRole("article").getByRole("button", { name: /显示原文|显示中文/ }).first()).toBeVisible();
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
  const narrative = page.getByLabel("叙事框架");
  await expect(narrative.getByText("强调点：").first()).toBeVisible();
  await expect(narrative.getByText("官方仍在核实原因")).toBeVisible();
  await expect(narrative.getByText("关键措辞：").first()).toBeVisible();
  await narrative.getByRole("button", { name: "显示原文" }).first().click();
  await expect(narrative.getByText("security")).toBeVisible();
  const sourceGraph = page.getByLabel("来源图谱");
  await expect(sourceGraph.getByText("路透社")).toBeVisible();
  await expect(sourceGraph.getByText("伊朗伊斯兰共和国通讯社")).toBeVisible();
  await expect(sourceGraph.getByText(/路透社 · 英国 · 原文语言：英文/)).toBeVisible();
  await expect(sourceGraph.getByText(/伊朗伊斯兰共和国通讯社 · 伊朗 · 原文语言：英文/)).toBeVisible();
  await expect(sourceGraph.getByText("路透社 / Reuters")).toHaveCount(0);
  await expect(sourceGraph.getByText("伊朗伊斯兰共和国通讯社 / IRNA")).toHaveCount(0);
  await expect(page.getByText("原文语言：英文").first()).toBeVisible();
  const sourceAgency = page.getByRole("article").getByLabel("新闻机构");
  await expect(sourceAgency.getByText("路透社")).toBeVisible();
  await expect(sourceAgency.getByText("Reuters")).toHaveCount(0);
  await sourceAgency.getByRole("button", { name: "显示原文" }).click();
  await expect(sourceAgency.getByText("Reuters")).toBeVisible();
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
  await page.getByRole("article").getByRole("button", { name: "显示原文" }).first().click();
  await expect(page.getByText("Officials report 12 casualties after overnight strike")).toBeVisible();
  await expect(page.getByText("选中的事实片段")).toBeVisible();
  if ((page.viewportSize()?.width ?? 0) >= 768) {
    await page.getByRole("button", { name: "地区", exact: true }).click();
    await expect(page.locator("span").filter({ hasText: /^欧洲$/ })).toBeVisible();
  }
});

test("does not show stale english translation cache as Chinese", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      return route.fulfill({
        json: {
          data: [{
            id: "evt-stale-translation",
            title: "旧翻译缓存测试事件",
            summary: "用于确认英文缓存不会冒充中文。",
            category: "politics",
            region_primary: "europe",
            status: "active",
            article_count: 1,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 35,
            last_updated_at: new Date().toISOString(),
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-stale-translation/articles") {
      return route.fulfill({
        json: {
          data: [{
            id: "article-stale",
            source_id: "reuters",
            external_url: "https://example.test/stale",
            title_original: "Original English title",
            title_translated: "Old cached English title",
            content_original: "Original English article body with enough text to be a normal report. It should only appear after the user chooses the original view.",
            content_translated: "Old cached English body that must not appear inside the Chinese translation view.",
            language: "en",
            author: "Reuters",
            published_at: new Date().toISOString(),
            source: { id: "reuters", name: "Reuters", country: "United Kingdom", region: "europe", language: "en", composite_credibility: 86 },
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/articles/article-stale/translate") {
      return route.fulfill({ status: 503, json: { detail: "translation unavailable" } });
    }
    if (url.pathname === "/api/v1/events/evt-stale-translation/analysis") {
      return route.fulfill({
        json: {
          data: {
            event_id: "evt-stale-translation",
            summary: "中文分析摘要",
            analysis_version: 1,
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

  await expect(page.getByText("自动翻译暂不可用：当前显示中文说明，可点击“显示原文”查看来源原文。")).toBeVisible();
  await expect(page.getByText("这篇报道暂时没有可用的中文标题")).toBeVisible();
  await expect(page.getByText("基于 1 篇报道")).toBeVisible();
  await expect(page.getByText("署名：路透社")).toBeVisible();
  await expect(page.getByText("署名：Reuters")).toHaveCount(0);
  await expect(page.getByText("Old cached English title")).toHaveCount(0);
  await expect(page.getByText("Old cached English body that must not appear inside the Chinese translation view.")).toHaveCount(0);
});

test("keeps event title informative when event translation fails", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      return route.fulfill({
        json: {
          data: [{
            id: "evt-event-translation-failure",
            title: "Original English event headline",
            title_en: "Original English event headline",
            summary: "Original English event summary.",
            category: "politics",
            region_primary: "europe",
            status: "active",
            article_count: 0,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 35,
            last_updated_at: new Date().toISOString(),
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-event-translation-failure/translate") {
      return route.fulfill({ status: 503, json: { detail: "translation unavailable" } });
    }
    if (url.pathname === "/api/v1/events/evt-event-translation-failure/articles") {
      return route.fulfill({ json: { data: [] } });
    }
    if (url.pathname === "/api/v1/events/evt-event-translation-failure/analysis") {
      return route.fulfill({
        json: {
          data: {
            event_id: "evt-event-translation-failure",
            summary: "本站暂未形成详细分析。",
            analysis_version: 1,
            article_count_at_analysis: 0,
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

  await expect(page.locator("h1", { hasText: "事件标题暂未成功翻译：Original English event headline" })).toBeVisible();
  await expect(page.getByText("中文翻译暂时不可用")).toHaveCount(0);
});

test("labels source original name with the source language", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      return route.fulfill({
        json: {
          data: [{
            id: "evt-source-language",
            title: "来源语言测试事件",
            summary: "用于确认来源原名语言标注。",
            category: "politics",
            region_primary: "middle_east",
            status: "active",
            article_count: 1,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 35,
            last_updated_at: new Date().toISOString(),
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-source-language/articles") {
      return route.fulfill({
        json: {
          data: [{
            id: "article-source-language",
            source_id: "irna",
            external_url: "https://example.test/irna",
            title_original: "Local agency report",
            title_translated: "当地通讯社报道",
            content_original: "Original report body with enough text to render a normal article panel.",
            content_translated: "这是一篇用于测试来源语言标注的中文正文。",
            language: "fa",
            published_at: new Date().toISOString(),
            source: { id: "irna", name: "IRNA", country: "Iran", region: "middle_east", language: "fa", composite_credibility: 48 },
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-source-language/analysis") {
      return route.fulfill({
        json: {
          data: {
            event_id: "evt-source-language",
            summary: "中文分析摘要",
            analysis_version: 1,
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

  const sourceAgency = page.getByRole("article").getByLabel("新闻机构");
  await sourceAgency.getByRole("button", { name: "显示原文" }).click();
  await expect(sourceAgency.getByText("IRNA")).toBeVisible();
  await expect(sourceAgency.getByText("原文语言：波斯文")).toBeVisible();
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

test("refreshes reports after a live collection update", async ({ page }) => {
  await page.addInitScript(() => {
    const sockets: Array<{ onmessage?: (event: { data: string }) => void; onopen?: (event: Event) => void }> = [];
    (window as unknown as { __mockCollectionSockets: typeof sockets }).__mockCollectionSockets = sockets;
    (window as unknown as { __sendArticlesCollected: () => void }).__sendArticlesCollected = () => {
      for (const socket of sockets) {
        socket.onmessage?.({ data: JSON.stringify({ type: "articles_collected", event_id: "evt-2" }) });
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
  let articleCalls = 0;
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      return route.fulfill({
        json: {
          data: [{
            id: "evt-2",
            title: "采集测试事件",
            summary: "用于验证采集更新。",
            category: "politics",
            region_primary: "europe",
            status: "active",
            article_count: 1,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 40,
            last_updated_at: new Date().toISOString(),
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-2/articles") {
      articleCalls += 1;
      return route.fulfill({
        json: {
          data: articleCalls === 1 ? [] : [{
            id: "article-1",
            source_id: "reuters",
            external_url: "https://example.test/article-1",
            title_original: "Collected report appears after live update",
            title_translated: "实时更新后出现的新报道",
            content_original: "A newly collected report has enough body text for the article panel.",
            content_translated: "这是一篇实时采集后出现的新报道，正文已经进入文章面板。",
            language: "en",
            published_at: new Date().toISOString(),
            source: { id: "reuters", name: "Reuters", country: "United Kingdom", region: "europe", language: "en", composite_credibility: 86 },
          }],
        },
      });
    }
    if (url.pathname === "/api/v1/events/evt-2/analysis") {
      return route.fulfill({
        json: {
          data: {
            event_id: "evt-2",
            summary: "采集更新测试分析",
            analysis_version: 1,
            article_count_at_analysis: 0,
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

  await expect(page.getByText("这个事件暂时没有关联报道")).toBeVisible();
  await page.waitForFunction(() => (window as unknown as { __mockCollectionSockets?: unknown[] }).__mockCollectionSockets?.length);
  await page.evaluate(() => (window as unknown as { __sendArticlesCollected: () => void }).__sendArticlesCollected());
  await expect(page.getByText("实时更新 · 新报道已采集")).toBeVisible();
  await expect(page.getByText("实时更新后出现的新报道")).toBeVisible();
  expect(articleCalls).toBeGreaterThanOrEqual(2);
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

test("ignores stale event responses after filters change", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/events") {
      const event = url.searchParams.get("category") === "technology"
        ? {
            id: "filtered-event",
            title: "筛选后的科技事件",
            summary: "新筛选结果。",
            category: "technology",
            region_primary: "east_asia",
            status: "active",
            article_count: 0,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 30,
            last_updated_at: new Date().toISOString(),
          }
        : {
            id: "stale-event",
            title: "过期的初始事件",
            summary: "慢请求返回的旧结果。",
            category: "conflict",
            region_primary: "middle_east",
            status: "active",
            article_count: 0,
            source_count: 1,
            language_count: 1,
            region_count: 1,
            heat_score: 80,
            last_updated_at: new Date().toISOString(),
          };
      const delay = url.searchParams.get("category") === "technology" ? 0 : 600;
      return new Promise<void>((resolve) => {
        setTimeout(() => {
          void route.fulfill({ json: { data: [event] } }).then(resolve);
        }, delay);
      });
    }
    if (url.pathname.endsWith("/articles")) {
      return route.fulfill({ json: { data: [] } });
    }
    if (url.pathname.endsWith("/analysis")) {
      return route.fulfill({
        json: {
          data: {
            event_id: "filtered-event",
            summary: "筛选事件分析",
            analysis_version: 1,
            article_count_at_analysis: 0,
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
  await page.locator("select[aria-label='按分类筛选']").last().selectOption("technology");

  await expect(page.locator("h1", { hasText: "筛选后的科技事件" })).toBeVisible();
  await page.waitForTimeout(800);
  await expect(page.locator("h1", { hasText: "筛选后的科技事件" })).toBeVisible();
  await expect(page.getByText("过期的初始事件")).toHaveCount(0);
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
