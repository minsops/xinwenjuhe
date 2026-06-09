import { Activity, ListChecks, RefreshCw } from "lucide-react";
import { useState } from "react";
import type { TaskOverview } from "../../types/task";
import { refreshSourceCredibility, startClusterNewArticles, startCollectActiveSources, startCollectHotEvents } from "../../services/api";
import { formatDate } from "../../utils/formatDate";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  overview: TaskOverview;
};

export function OperationsPanel({ overview }: Props) {
  const text = getUiText();
  const [lastTask, setLastTask] = useState<string | undefined>();
  const recent = overview.history.slice(0, 5);
  async function run(action: () => Promise<{ task_id: string }>) {
    const result = await action();
    setLastTask(result.task_id);
  }
  return (
    <section className="border-b border-stone-300 bg-white p-3 dark:border-stone-700 dark:bg-stone-900">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Activity className="h-4 w-4 text-civic dark:text-cyan-200" />
          {text.operationsTitle}
        </div>
        <Badge tone={overview.queue_depth && overview.queue_depth > 0 ? "yellow" : "green"}>
          {text.queueDepth} {overview.queue_depth ?? "n/a"}
        </Badge>
      </div>
      <div className="mb-3 text-xs leading-5 text-stone-500 dark:text-stone-400">{text.operationsSubtitle}</div>
      <div className="mb-3 grid gap-2">
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startCollectActiveSources)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {text.collectSources}
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startClusterNewArticles)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {text.clusterArticles}
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startCollectHotEvents)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {text.collectHotEvents}
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(refreshSourceCredibility)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          {text.refreshCredibility}
        </button>
        {lastTask ? <div className="truncate text-xs text-stone-500">{text.queuedTask} {lastTask}</div> : null}
      </div>
      <div className="mb-2 text-xs font-medium text-stone-500 dark:text-stone-400">{text.recentTasks}</div>
      <div className="space-y-2">
        {recent.length ? recent.map((item) => (
          <div key={`${item.task_id}-${item.updated_at}`} className="rounded border border-stone-200 p-2 text-xs dark:border-stone-700">
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex min-w-0 items-center gap-1">
                <ListChecks className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{formatTaskName(item.step ?? item.task_id)}</span>
              </span>
              <Badge tone={item.status === "complete" ? "green" : "blue"}>{formatTaskStatus(item.status)}</Badge>
            </div>
            <div className="mt-1 truncate text-stone-500">{item.updated_at ? formatDate(item.updated_at) : item.task_id}</div>
          </div>
        )) : <div className="text-xs text-stone-500">{text.noRecentTasks}</div>}
      </div>
    </section>
  );
}

function formatTaskStatus(status?: string | null): string {
  const map: Record<string, string> = {
    complete: "完成",
    running: "运行中",
    queued: "排队中",
    failed: "失败",
    unknown: "未知"
  };
  return map[status ?? "unknown"] ?? status ?? map.unknown;
}

function formatTaskName(name?: string | null): string {
  const value = name ?? "";
  const map: Record<string, string> = {
    collect_active_sources: "采集全部来源",
    collect_hot_events: "补采热门事件",
    collect_single_source: "采集单个来源",
    cluster_new_articles: "聚类新文章",
    refresh_source_credibility: "刷新来源可信度",
    process_event_pipeline: "事件分析流水线",
    translate_articles: "翻译文章",
    deduplicate_articles: "去重文章",
    extract_facts: "提取事实",
    detect_contradictions: "检测矛盾",
    analyze_narratives: "分析叙事",
    generate_consensus_map: "生成共识图",
    notify_clients: "通知前端"
  };
  const parts = value.split(".");
  const shortName = parts[parts.length - 1] || value;
  return map[shortName] ?? (shortName || "未知任务");
}
