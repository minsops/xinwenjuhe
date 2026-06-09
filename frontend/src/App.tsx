import { useMemo, useState } from "react";
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
import { formatRegion, getUiText } from "./utils/i18n";

export default function App() {
  const text = getUiText();
  const [darkMode, setDarkMode] = useState(false);
  const [search, setSearch] = useState("");
  const [activePane, setActivePane] = useState<"news" | "analysis">("news");
  const [regionFilter, setRegionFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [sort, setSort] = useState<"heat" | "latest">("heat");
  const [focusedArticleId, setFocusedArticleId] = useState<string | undefined>();
  const [highlightedFact, setHighlightedFact] = useState<string | undefined>();
  const [analysisRefreshKey, setAnalysisRefreshKey] = useState(0);
  const { events, selected, setSelected } = useEvent({
    region: regionFilter || undefined,
    category: categoryFilter || undefined,
    sort,
  });
  const articles = useArticles(selected?.id);
  const analysis = useAnalysis(selected?.id, analysisRefreshKey);
  const taskOverview = useTaskProgress();
  const live = useEventSocket(selected?.id);
  const filteredEvents = useMemo(
    () => events.filter((event) => event.title.toLowerCase().includes(search.toLowerCase())),
    [events, search]
  );

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="min-h-screen bg-paper text-ink dark:bg-stone-950 dark:text-stone-50">
        <TopBar darkMode={darkMode} onToggleDarkMode={() => setDarkMode((value) => !value)} search={search} onSearch={setSearch} />
        <div className="flex">
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
          <div className="min-w-0 flex-1">
            <div className="border-b border-stone-300 bg-stone-100 p-3 dark:border-stone-700 dark:bg-stone-950 xl:hidden">
              <div className="grid gap-2 sm:grid-cols-2">
                <select
                  aria-label="Selected event"
                  className="focus-ring h-10 min-w-0 rounded border border-stone-300 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-900"
                  value={selected?.id ?? ""}
                  onChange={(event) => {
                    const next = filteredEvents.find((item) => item.id === event.target.value);
                    if (next) {
                      setSelected(next);
                    }
                  }}
                >
                  {filteredEvents.map((event) => (
                    <option key={event.id} value={event.id}>{event.title}</option>
                  ))}
                </select>
                <select
                  aria-label="Sort events"
                  className="focus-ring h-10 rounded border border-stone-300 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-900"
                  value={sort}
                  onChange={(event) => setSort(event.target.value as "heat" | "latest")}
                >
                  <option value="heat">{text.heat}</option>
                  <option value="latest">{text.latest}</option>
                </select>
                <select
                  aria-label="Filter by region"
                  className="focus-ring h-10 rounded border border-stone-300 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-900"
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
                  aria-label="Filter by category"
                  className="focus-ring h-10 rounded border border-stone-300 bg-white px-3 text-sm dark:border-stone-700 dark:bg-stone-900"
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
            <div className="xl:hidden">
              <OperationsPanel overview={taskOverview} />
            </div>
            {live.message ? (
              <div className="border-b border-cyan-200 bg-cyan-50 px-4 py-2 text-sm text-cyan-950 dark:border-cyan-900 dark:bg-cyan-950 dark:text-cyan-100">
                {live.message.type ?? "event_update"}
              </div>
            ) : null}
            <div className="grid grid-cols-2 border-b border-stone-300 bg-white p-2 dark:border-stone-700 dark:bg-stone-900 lg:hidden">
              <button className={`rounded px-3 py-2 text-sm ${activePane === "news" ? "bg-civic text-white" : ""}`} onClick={() => setActivePane("news")}>{text.news}</button>
              <button className={`rounded px-3 py-2 text-sm ${activePane === "analysis" ? "bg-civic text-white" : ""}`} onClick={() => setActivePane("analysis")}>{text.analysis}</button>
            </div>
            <DualPanelLayout
              activePane={activePane}
              left={
                <NewsPanel
                  articles={articles}
                  selectedArticleId={focusedArticleId}
                  highlightedFact={highlightedFact}
                  onArticleSelect={(articleId) => {
                    setFocusedArticleId(articleId);
                    setHighlightedFact(undefined);
                  }}
                />
              }
              right={analysis ? (
                <AnalysisPanel
                  analysis={analysis}
                  eventId={selected?.id}
                  onFactSelect={(articleId, fact) => {
                    setFocusedArticleId(articleId);
                    setHighlightedFact(fact);
                    setActivePane("news");
                  }}
                  onReanalyze={() => setAnalysisRefreshKey((value) => value + 1)}
                />
              ) : <div><div className="p-4 text-sm text-stone-500">{text.loadingAnalysis}</div><Skeleton lines={6} /></div>}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
