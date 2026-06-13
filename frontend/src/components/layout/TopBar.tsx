import { Moon, Search, ShieldCheck, Sun } from "lucide-react";
import { getUiText } from "../../utils/i18n";

type Props = {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  search: string;
  onSearch: (value: string) => void;
};

export function TopBar({ darkMode, onToggleDarkMode, search, onSearch }: Props) {
  const text = getUiText();
  return (
    <header className="sticky top-0 z-40 border-b border-white/70 bg-white/90 shadow-sm backdrop-blur-xl dark:border-stone-800 dark:bg-stone-950/90">
      <div className="mx-auto flex h-16 w-full max-w-[1920px] items-center gap-4 px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-civic text-white shadow-sm dark:bg-cyan-700">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-lg font-black tracking-tight text-civic dark:text-cyan-100">TruthPuzzle</div>
            <div className="hidden text-xs text-stone-500 dark:text-stone-400 sm:block">多源新闻聚合与结构化核验</div>
          </div>
        </div>
        <div className="relative ml-auto w-full max-w-2xl">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
          <input
            className="focus-ring h-10 w-full rounded-2xl border border-stone-200 bg-stone-50/80 pl-10 pr-3 text-sm shadow-inner placeholder:text-stone-400 dark:border-stone-800 dark:bg-stone-900/80"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
            placeholder={text.searchEvents}
          />
        </div>
        <button
          className="focus-ring grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-stone-200 bg-white text-stone-700 shadow-sm transition hover:-translate-y-0.5 hover:shadow dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100"
          onClick={onToggleDarkMode}
          title="Toggle theme"
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
      </div>
    </header>
  );
}
