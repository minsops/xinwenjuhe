import { Activity, ListChecks, RefreshCw } from "lucide-react";
import { useState } from "react";
import type { TaskOverview } from "../../types/task";
import { refreshSourceCredibility, startClusterNewArticles, startCollectActiveSources, startCollectHotEvents } from "../../services/api";
import { formatDate } from "../../utils/formatDate";
import { Badge } from "../shared/Badge";

type Props = {
  overview: TaskOverview;
};

export function OperationsPanel({ overview }: Props) {
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
          Operations
        </div>
        <Badge tone={overview.queue_depth && overview.queue_depth > 0 ? "yellow" : "green"}>
          Queue {overview.queue_depth ?? "n/a"}
        </Badge>
      </div>
      <div className="mb-3 grid gap-2">
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startCollectActiveSources)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Collect sources
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startClusterNewArticles)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Cluster articles
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(startCollectHotEvents)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Collect hot events
        </button>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded border border-stone-300 px-3 py-2 text-xs dark:border-stone-700"
          onClick={() => void run(refreshSourceCredibility)}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh credibility
        </button>
        {lastTask ? <div className="truncate text-xs text-stone-500">Queued {lastTask}</div> : null}
      </div>
      <div className="space-y-2">
        {recent.length ? recent.map((item) => (
          <div key={`${item.task_id}-${item.updated_at}`} className="rounded border border-stone-200 p-2 text-xs dark:border-stone-700">
            <div className="flex items-center justify-between gap-2">
              <span className="inline-flex min-w-0 items-center gap-1">
                <ListChecks className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{item.step ?? item.task_id}</span>
              </span>
              <Badge tone={item.status === "complete" ? "green" : "blue"}>{item.status ?? "unknown"}</Badge>
            </div>
            <div className="mt-1 truncate text-stone-500">{item.updated_at ? formatDate(item.updated_at) : item.task_id}</div>
          </div>
        )) : <div className="text-xs text-stone-500">No recent tasks.</div>}
      </div>
    </section>
  );
}
