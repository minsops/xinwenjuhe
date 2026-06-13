import type { Event } from "../../types/event";
import { formatDate } from "../../utils/formatDate";
import { formatCategory, formatRegion, formatStatus, getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  event: Event;
};

export function EventMeta({ event }: Props) {
  const text = getUiText();
  const hot = event.heat_score >= 70;
  const summary = event.summary_zh ?? event.summary;
  return (
    <section className="overflow-hidden rounded-3xl border border-white/70 bg-white/90 p-5 shadow-sm backdrop-blur dark:border-stone-800 dark:bg-stone-950/90">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-5xl">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-civic dark:text-cyan-200">
            <span>{formatRegion(event.region_primary)}</span>
            <span className="h-1 w-1 rounded-full bg-stone-300 dark:bg-stone-700" />
            <span>{formatCategory(event.category)}</span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-black leading-tight tracking-tight text-stone-950 dark:text-white lg:text-3xl">{event.title_zh ?? event.title}</h1>
            <Badge tone={hot ? "red" : "blue"}>{hot ? text.hotStatus : formatStatus(event.status)}</Badge>
          </div>
          {summary ? <p className="mt-3 max-w-4xl text-sm leading-6 text-stone-600 dark:text-stone-300">{summary}</p> : null}
        </div>
        <div className="grid min-w-[18rem] grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
          <MetricPill label={text.sources} value={event.source_count} />
          <MetricPill label={text.regions} value={event.region_count} />
          <MetricPill label={text.languages} value={event.language_count} />
          <MetricPill label={text.heat} value={Math.round(event.heat_score)} />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
        <span className="rounded-full bg-stone-100 px-3 py-1 dark:bg-stone-900">{event.article_count} {text.reports}</span>
        <span className="rounded-full bg-stone-100 px-3 py-1 dark:bg-stone-900">更新：{formatDate(event.last_updated_at)}</span>
      </div>
    </section>
  );
}

function MetricPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-stone-100 bg-stone-50 px-3 py-2 text-center dark:border-stone-800 dark:bg-stone-900/80">
      <div className="text-lg font-black text-stone-950 dark:text-white">{value}</div>
      <div className="text-xs text-stone-500 dark:text-stone-400">{label}</div>
    </div>
  );
}
