import { Moon, Search, Sun } from "lucide-react";
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
    <header className="flex h-14 items-center gap-3 border-b border-stone-300 bg-paper px-4 dark:border-stone-700 dark:bg-stone-950">
      <div className="text-lg font-semibold tracking-normal text-civic dark:text-cyan-200">TruthPuzzle</div>
      <div className="relative max-w-xl flex-1">
        <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-stone-500" />
        <input
          className="focus-ring h-9 w-full rounded border border-stone-300 bg-white pl-9 pr-3 text-sm dark:border-stone-700 dark:bg-stone-900"
          value={search}
          onChange={(event) => onSearch(event.target.value)}
          placeholder={text.searchEvents}
        />
      </div>
      <button className="focus-ring rounded border border-stone-300 p-2 dark:border-stone-700" onClick={onToggleDarkMode} title="Toggle theme">
        {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </header>
  );
}
