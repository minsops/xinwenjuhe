import { Search } from "lucide-react";
import type { Event } from "../../types/event";
import type { TaskOverview } from "../../types/task";
import { formatRegion, getUiText } from "../../utils/i18n";
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

const selectClass =
  "focus-ring h-10 rounded-xl border border-stone-200 bg-white px-3 text-sm text-stone-800 shadow-sm dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100";

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
    <nav className="soft-scrollbar sticky top-20 hidden max-h-[calc(100vh-6rem)] w-[22rem] shrink-0 overflow-y-auto rounded-3xl border border-white/70 bg-white/85 p-3 shadow-sm backdrop-blur dark:border-stone-800 dark:bg-stone-950/85 xl:block" aria-label="事件列表">
      <div className="mb-4 overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-950 via-cyan-900 to-slate-900 p-4 text-white shadow-sm">
        <div className="text-xs font-semibold tracking-[0.22em] text-cyan-100/80">事件雷达</div>
        <div className="mt-2 text-2xl font-black tracking-tight">事件雷达</div>
        <div className="mt-1 text-sm text-cyan-50/80">{events.length} 条事件 · 当前按{text[sort]}排序</div>
      </div>
      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
        <input
          className="focus-ring h-11 w-full rounded-2xl border border-stone-200 bg-stone-50/90 pl-10 pr-3 text-sm shadow-inner placeholder:text-stone-400 dark:border-stone-800 dark:bg-stone-900/90"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder={text.searchEvents}
        />
      </div>
      <div className="mb-4 grid grid-cols-2 gap-2">
        <select className={selectClass} value={region} onChange={(event) => onRegionChange(event.target.value)}>
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
        <select className={selectClass} value={category} onChange={(event) => onCategoryChange(event.target.value)}>
          <option value="">{text.allCategories}</option>
          <option value="conflict">{text.conflict}</option>
          <option value="politics">{text.politics}</option>
          <option value="economy">{text.economy}</option>
          <option value="disaster">{text.disaster}</option>
          <option value="technology">{text.technology}</option>
        </select>
        <select className={`${selectClass} col-span-2`} value={sort} onChange={(event) => onSortChange(event.target.value as "heat" | "latest")}>
          <option value="heat">{text.heat}</option>
          <option value="latest">{text.latest}</option>
        </select>
      </div>
      <div className="space-y-2.5">
        {events.map((event) => (
          <EventCard key={event.id} event={event} selected={event.id === selectedId} onSelect={() => onSelect(event)} />
        ))}
        {!events.length ? (
          <div className="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-4 text-sm text-stone-500 dark:border-stone-800 dark:bg-stone-900/60 dark:text-stone-400">
            <div className="font-semibold text-stone-700 dark:text-stone-200">
              {search || region || category ? text.noEventsFiltered : text.noEventsTitle}
            </div>
            <div className="mt-1 leading-5">
              {search || region || category ? "当前筛选条件下没有事件。" : text.noEventsDescription}
            </div>
          </div>
        ) : null}
      </div>
      {taskOverview ? <div className="mt-4 overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-950"><OperationsPanel overview={taskOverview} /></div> : null}
    </nav>
  );
}
