import type { Event } from "../../types/event";
import { formatDate } from "../../utils/formatDate";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  event: Event;
  selected: boolean;
  onSelect: () => void;
};

export function EventCard({ event, selected, onSelect }: Props) {
  const text = getUiText();
  const hot = event.heat_score >= 70;
  return (
    <button
      className={`focus-ring w-full rounded border p-3 text-left ${
        selected ? "border-civic bg-cyan-50 dark:bg-cyan-950" : "border-stone-300 bg-white dark:border-stone-700 dark:bg-stone-900"
      }`}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">{event.title}</h3>
        <div className="flex shrink-0 items-center gap-2">
          {hot ? <span className="h-2 w-2 animate-pulse rounded-full bg-red-600" title={text.hotStatus} /> : null}
          <Badge tone={hot ? "red" : "blue"}>{Math.round(event.heat_score)}</Badge>
        </div>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-stone-600 dark:text-stone-300">{event.summary ?? "No summary yet."}</p>
      <div className="mt-3 flex flex-wrap gap-x-2 gap-y-1 text-xs text-stone-500">
        <span>{event.article_count} {text.reports}</span>
        <span>{event.source_count} {text.sources}</span>
        <span>{event.region_count} {text.regions}</span>
        <span>{event.language_count} {text.languages}</span>
      </div>
      <div className="mt-2 text-xs text-stone-500">{formatDate(event.last_updated_at)}</div>
    </button>
  );
}
