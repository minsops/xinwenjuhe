import { useState } from "react";
import type { Event } from "../../types/event";
import { formatDate } from "../../utils/formatDate";
import { formatLanguage, formatRegion, getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  event: Event;
  selected: boolean;
  onSelect: () => void;
};

export function EventCard({ event, selected, onSelect }: Props) {
  const text = getUiText();
  const [showOriginal, setShowOriginal] = useState(false);
  const hot = event.heat_score >= 70;
  const hasOriginalEvent = Boolean(event.title_en || event.summary);
  const title = showOriginal ? event.title_en ?? event.title : event.title_zh ?? event.title;
  const summary = showOriginal ? event.summary ?? event.summary_zh : event.summary_zh ?? event.summary;
  const originalLanguage = event.language_count > 1 ? "multi" : "auto";
  return (
    <button
      className={`focus-ring group relative w-full overflow-hidden rounded-2xl border p-3.5 text-left transition duration-200 ${
        selected
          ? "border-civic bg-cyan-50 shadow-sm ring-1 ring-cyan-800/10 dark:bg-cyan-950/40"
          : "border-stone-200 bg-white hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow-sm dark:border-stone-800 dark:bg-stone-900/80 dark:hover:border-cyan-800"
      }`}
      onClick={onSelect}
    >
      <span className={`absolute inset-y-0 left-0 w-1 ${hot ? "bg-red-500" : "bg-civic dark:bg-cyan-600"}`} />
      <div className="flex items-start justify-between gap-3 pl-1">
        <div className="min-w-0">
          <div className="mb-1 flex flex-wrap items-center gap-1.5 text-xs text-stone-500 dark:text-stone-400">
            <span className="rounded-full bg-stone-100 px-2 py-0.5 dark:bg-stone-800">{formatRegion(event.region_primary)}</span>
            <span className="rounded-full bg-stone-100 px-2 py-0.5 dark:bg-stone-800">{event.category ?? text.analysis}</span>
          </div>
          <h3 className="text-[15px] font-bold leading-snug text-stone-950 dark:text-stone-50">{title}</h3>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {hot ? <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-red-500 shadow-[0_0_0_4px_rgba(239,68,68,0.12)]" title={text.hotStatus} /> : null}
          <Badge tone={hot ? "red" : "blue"}>{Math.round(event.heat_score)}</Badge>
        </div>
      </div>
      <p className="mt-2.5 line-clamp-3 pl-1 text-sm leading-6 text-stone-600 dark:text-stone-300">{summary ?? "暂无概要。"}</p>
      <div className="mt-3 flex items-center justify-between gap-2 pl-1 text-xs text-stone-500 dark:text-stone-400">
        <span>{text.originalLanguage}：{formatLanguage(originalLanguage)}</span>
        {hasOriginalEvent ? (
          <span
            role="button"
            tabIndex={0}
            className="rounded-full border border-stone-200 bg-white px-2.5 py-1 font-medium text-stone-700 transition hover:border-cyan-300 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-200"
            onClick={(eventClick) => {
              eventClick.stopPropagation();
              setShowOriginal((value) => !value);
            }}
            onKeyDown={(eventKey) => {
              if (eventKey.key === "Enter" || eventKey.key === " ") {
                eventKey.preventDefault();
                eventKey.stopPropagation();
                setShowOriginal((value) => !value);
              }
            }}
          >
            {showOriginal ? text.showChinese : text.original}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid grid-cols-4 gap-1.5 pl-1 text-center text-xs text-stone-500 dark:text-stone-400">
        <Metric value={event.article_count} label={text.reports} />
        <Metric value={event.source_count} label={text.sources} />
        <Metric value={event.region_count} label={text.regions} />
        <Metric value={event.language_count} label={text.languages} />
      </div>
      <div className="mt-2.5 pl-1 text-xs text-stone-400">{formatDate(event.last_updated_at)}</div>
    </button>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <span className="rounded-xl bg-stone-50 px-1.5 py-1 dark:bg-stone-800/70">
      <span className="font-semibold text-stone-700 dark:text-stone-200">{value}</span> {label}
    </span>
  );
}
