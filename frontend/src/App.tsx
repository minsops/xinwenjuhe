import { useEffect, useMemo, useState } from "react";
import { AnalysisPanel } from "./components/analysis-panel/AnalysisPanel";
import { EventList } from "./components/event-list/EventList";
import { DualPanelLayout } from "./components/layout/DualPanelLayout";
import { EventMeta } from "./components/layout/EventMeta";
import { OperationsPanel } from "./components/layout/OperationsPanel";
import { TopBar } from "./components/layout/TopBar";
import { NewsPanel } from "./components/news-panel/NewsPanel";
import { Skeleton } from "./components/shared/Skeleton";
import { useAnalysis } from "./hooks/useAnalysis";
import { useArticles } from "./hooks/useArticles";
import { useEventSocket } from "./hooks/useEventSocket";
import { useEvent } from "./hooks/useEvent";
import { useTaskProgress } from "./hooks/useTaskProgress";
import { formatRegion, formatSourceChineseName, getUiText } from "./utils/i18n";

const mobileSelectClass =
  "focus-ring h-11 min-w-0 rounded-xl border border-stone-200 bg-white px-3 text-sm text-stone-800 shadow-sm dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100";

export default function App() {
  const text = getUiText();
  const [darkMode, setDarkMode] = useState(false);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [sort, setSort] = useState<"heat" | "latest">("heat");
  const [focusedArticleId, setFocusedArticleId] = useState<string | undefined>();
  const [highlightedFact, setHighlightedFact] = useState<string | undefined>();
  const [analysisRefreshKey, setAnalysisRefreshKey] = useState(0);
  const [articleRefreshKey, setArticleRefreshKey] = useState(0);
  const { events, selected, setSelected } = useEvent({
    region: regionFilter || undefined,
    category: categoryFilter || undefined,
    sort,
  });
  const articles = useArticles(selected?.id, articleRefreshKey);
  const analysis = useAnalysis(selected?.id, analysisRefreshKey);
  const taskOverview = useTaskProgress();
  const live = useEventSocket(selected?.id);

  useEffect(() => {
    if (!selected?.id || !live.message?.type) return;
    if (live.message.event_id && live.message.event_id !== selected.id) return;
    if (live.message.type === "analysis_updated") {
      setAnalysisRefreshKey((value) => value + 1);
    }
    if (live.message.type === "articles_collected" || live.message.type === "backfill_complete") {
      setArticleRefreshKey((value) => value + 1);
    }
    if (live.message.type === "backfill_complete") {
      setAnalysisRefreshKey((value) => value + 1);
    }
  }, [live.message, selected?.id]);

  const filteredEvents = useMemo(
    () => {
      const query = search.trim().toLowerCase();
      if (!query) return events;
      return events.filter((event) => searchableEventText(event).includes(query));
    },
    [events, search]
  );
  const sourceLabels = useMemo(
    () =>
      Object.fromEntries(
        articles
          .filter((article) => article.source)
          .map((article) => [
            article.source_id,
            formatSourceChineseName(article.source?.name, article.source?.name_en),
          ])
      ),
    [articles]
  );

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="min-h-screen bg-[#f3f7f8] text-ink dark:bg-stone-950 dark:text-stone-50">
        <TopBar darkMode={darkMode} onToggleDarkMode={() => setDarkMode((value) => !value)} search={search} onSearch={setSearch} />
        <div className="mx-auto flex w-full max-w-[1920px] gap-4 px-3 py-4 sm:px-5">
          <EventList
            events={filteredEvents}
            selectedId={selected?.id}
            onSelect={setSelected}
            taskOverview={taskOverview}
            region={regionFilter}
            category={categoryFilter}
            sort={sort}
            search={search}
            onSearch={setSearch}
            onRegionChange={setRegionFilter}
            onCategoryChange={setCategoryFilter}
            onSortChange={setSort}
          />
          <div className="min-w-0 flex-1 space-y-4">
            <div className="rounded-2xl border border-stone-200 bg-white/90 p-3 shadow-sm dark:border-stone-800 dark:bg-stone-950/90 xl:hidden">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-civic dark:text-cyan-200">事件筛选</div>
                  <div className="text-sm text-stone-500 dark:text-stone-400">{filteredEvents.length} 条匹配结果</div>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <select
                  aria-label="选择事件"
                  className={mobileSelectClass}
                  value={selected?.id ?? ""}
                  onChange={(event) => {
                    const next = filteredEvents.find((item) => item.id === event.target.value);
                    if (next) {
                      setSelected(next);
                    }
                  }}
                >
                  {filteredEvents.map((event) => (
                    <option key={event.id} value={event.id}>{eventDisplayTitle(event)}</option>
                  ))}
                </select>
                <select
                  aria-label="事件排序"
                  className={mobileSelectClass}
                  value={sort}
                  onChange={(event) => setSort(event.target.value as "heat" | "latest")}
                >
                  <option value="heat">{text.heat}</option>
                  <option value="latest">{text.latest}</option>
                </select>
                <select
                  aria-label="按地区筛选"
                  className={mobileSelectClass}
                  value={regionFilter}
                  onChange={(event) => setRegionFilter(event.target.value)}
                >
                  <option value="">{text.allRegions}</option>
                  <option value="north_america">{formatRegion("north_america")}</option>
                  <option value="europe">{formatRegion("europe")}</option>
                  <option value="east_asia">{formatRegion("east_asia")}</option>
                  <option value="middle_east">{formatRegion("middle_east")}</option>
                  <option value="south_asia">{formatRegion("south_asia")}</option>
                  <option value="africa">{formatRegion("africa")}</option>
                  <option value="latin_america">{formatRegion("latin_america")}</option>
                  <option value="russia_cis">{formatRegion("russia_cis")}</option>
                </select>
                <select
                  aria-label="按分类筛选"
                  className={mobileSelectClass}
                  value={categoryFilter}
                  onChange={(event) => setCategoryFilter(event.target.value)}
                >
                  <option value="">{text.allCategories}</option>
                  <option value="conflict">{text.conflict}</option>
                  <option value="politics">{text.politics}</option>
                  <option value="economy">{text.economy}</option>
                  <option value="disaster">{text.disaster}</option>
                  <option value="technology">{text.technology}</option>
                </select>
              </div>
            </div>
            {selected ? <EventMeta event={selected} /> : null}
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-950 xl:hidden">
              <OperationsPanel overview={taskOverview} />
            </div>
            {live.message ? (
              <div className="rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm font-medium text-cyan-950 shadow-sm dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-100">
                实时更新 · {formatLiveEventType(live.message.type)}
              </div>
            ) : null}
            <DualPanelLayout
              left={selected ? (
                analysis ? (
                  <AnalysisPanel
                    analysis={analysis}
                    eventId={selected.id}
                    sourceLabels={sourceLabels}
                    onFactSelect={(articleId, fact) => {
                      setFocusedArticleId(articleId);
                      setHighlightedFact(fact);
                    }}
                    onReanalyze={() => setAnalysisRefreshKey((value) => value + 1)}
                  />
                ) : <div><div className="p-4 text-sm text-stone-500">{text.loadingAnalysis}</div><Skeleton lines={6} /></div>
              ) : (
                <EmptyPanel title={text.noEventsTitle} description={text.noEventsDescription} />
              )}
              right={
                <NewsPanel
                  articles={articles}
                  hasSelectedEvent={Boolean(selected)}
                  selectedArticleId={focusedArticleId}
                  highlightedFact={highlightedFact}
                  onArticleSelect={(articleId) => {
                    setFocusedArticleId(articleId);
                    setHighlightedFact(undefined);
                  }}
                />
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-[420px] items-center justify-center bg-white p-6 text-center dark:bg-stone-950">
      <div className="max-w-md">
        <div className="text-lg font-black text-stone-900 dark:text-stone-50">{title}</div>
        <p className="mt-2 text-sm leading-6 text-stone-500 dark:text-stone-400">{description}</p>
      </div>
    </div>
  );
}

function formatLiveEventType(type?: string): string {
  const labels: Record<string, string> = {
    analysis_queued: "分析任务已加入队列",
    analysis_updated: "本站分析已更新",
    articles_collected: "新报道已采集",
    backfill_complete: "历史报道补全完成",
    event_merged: "事件已合并",
    event_split: "事件已拆分",
    heartbeat: "连接正常",
    message: "收到新消息",
  };
  return labels[type ?? ""] ?? "事件已更新";
}

function eventDisplayTitle(event: { title: string; title_zh?: string | null }): string {
  return event.title_zh || event.title;
}

function searchableEventText(event: {
  title: string;
  title_en?: string | null;
  title_zh?: string | null;
  summary?: string | null;
  summary_zh?: string | null;
  category?: string | null;
}): string {
  return [
    event.title,
    event.title_en,
    event.title_zh,
    event.summary,
    event.summary_zh,
    event.category,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}
