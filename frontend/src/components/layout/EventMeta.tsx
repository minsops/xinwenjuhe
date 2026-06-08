import type { Event } from "../../types/event";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  event: Event;
};

export function EventMeta({ event }: Props) {
  const text = getUiText();
  const hot = event.heat_score >= 70;
  return (
    <section className="border-b border-stone-300 bg-white px-4 py-3 dark:border-stone-700 dark:bg-stone-900">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold">{event.title}</h1>
        <Badge tone={hot ? "red" : "blue"}>{hot ? "Hot" : event.status}</Badge>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-stone-600 dark:text-stone-300">
        <span>{event.source_count} {text.sources}</span>
        <span>{event.region_count} {text.regions}</span>
        <span>{event.language_count} {text.languages}</span>
        <span>{text.heat} {Math.round(event.heat_score)}</span>
      </div>
    </section>
  );
}
