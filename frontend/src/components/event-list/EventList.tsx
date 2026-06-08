import { Search } from "lucide-react";
import type { Event } from "../../types/event";
import type { TaskOverview } from "../../types/task";
import { getUiText } from "../../utils/i18n";
import { OperationsPanel } from "../layout/OperationsPanel";
import { EventCard } from "./EventCard";

type Props = {
  events: Event[];
  selectedId?: string;
  onSelect: (event: Event) => void;
  taskOverview?: TaskOverview;
  region: string;
  category: string;
  sort: "heat" | "latest";
  search: string;
  onSearch: (value: string) => void;
  onRegionChange: (region: string) => void;
  onCategoryChange: (category: string) => void;
  onSortChange: (sort: "heat" | "latest") => void;
};

export function EventList({
  events,
  selectedId,
  onSelect,
  taskOverview,
  region,
  category,
  sort,
  search,
  onSearch,
  onRegionChange,
  onCategoryChange,
  onSortChange,
}: Props) {
  const text = getUiText();
  return (
    <nav className="hidden w-80 shrink-0 overflow-y-auto border-r border-stone-300 bg-stone-100 p-3 dark:border-stone-700 dark:bg-stone-950 xl:block">
      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-stone-500" />
        <input
          className="focus-ring h-9 w-full rounded border border-stone-300 bg-white pl-9 pr-3 text-sm dark:border-stone-700 dark:bg-stone-900"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder={text.searchEvents}
        />
      </div>
      <div className="mb-3 grid grid-cols-2 gap-2">
        <select
          className="focus-ring rounded border border-stone-300 bg-white px-2 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"
          value={region}
          onChange={(event) => onRegionChange(event.target.value)}
        >
          <option value="">{text.allRegions}</option>
          <option value="north_america">North America</option>
          <option value="europe">Europe</option>
          <option value="east_asia">East Asia</option>
          <option value="middle_east">Middle East</option>
          <option value="south_asia">South Asia</option>
          <option value="africa">Africa</option>
          <option value="latin_america">Latin America</option>
          <option value="russia_cis">Russia/CIS</option>
        </select>
        <select
          className="focus-ring rounded border border-stone-300 bg-white px-2 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"
          value={category}
          onChange={(event) => onCategoryChange(event.target.value)}
        >
          <option value="">{text.allCategories}</option>
          <option value="conflict">{text.conflict}</option>
          <option value="politics">{text.politics}</option>
          <option value="economy">{text.economy}</option>
          <option value="disaster">{text.disaster}</option>
          <option value="technology">{text.technology}</option>
        </select>
        <select
          className="focus-ring col-span-2 rounded border border-stone-300 bg-white px-2 py-2 text-sm dark:border-stone-700 dark:bg-stone-900"
          value={sort}
          onChange={(event) => onSortChange(event.target.value as "heat" | "latest")}
        >
          <option value="heat">{text.heat}</option>
          <option value="latest">{text.latest}</option>
        </select>
      </div>
      <div className="space-y-2">
        {events.map((event) => (
          <EventCard key={event.id} event={event} selected={event.id === selectedId} onSelect={() => onSelect(event)} />
        ))}
      </div>
      {taskOverview ? <div className="mt-3"><OperationsPanel overview={taskOverview} /></div> : null}
    </nav>
  );
}
