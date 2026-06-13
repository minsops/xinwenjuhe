import { useMemo, useState } from "react";
import type { Article } from "../../types/article";
import { formatCountry, formatLanguage, formatRegion, formatSourceName, getUiText } from "../../utils/i18n";
import { CredibilityBadge } from "./CredibilityBadge";

type Props = {
  articles: Article[];
  selectedId?: string;
  onSelect: (id: string) => void;
};

export function SourceTabs({ articles, selectedId, onSelect }: Props) {
  const text = getUiText();
  const [mode, setMode] = useState<"readable" | "credibility" | "region">("readable");
  const sortedByReadable = useMemo(() => articles, [articles]);
  const sortedByCredibility = useMemo(
    () =>
      [...articles].sort((left, right) => {
        const leftScore = left.source?.composite_credibility ?? -1;
        const rightScore = right.source?.composite_credibility ?? -1;
        return rightScore - leftScore || (left.source?.name ?? left.source_id).localeCompare(right.source?.name ?? right.source_id);
      }),
    [articles]
  );
  const groupedByRegion = useMemo(() => {
    const groups = new Map<string, Article[]>();
    for (const article of articles) {
      const region = article.source?.region ?? "unknown";
      groups.set(region, [...(groups.get(region) ?? []), article]);
    }
    return [...groups.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([region, rows]) => [
        region,
        rows.sort((left, right) => (left.source?.name ?? left.source_id).localeCompare(right.source?.name ?? right.source_id)),
      ] as const);
  }, [articles]);

  const renderButton = (article: Article) => {
    const selected = selectedId === article.id;
    return (
      <button
        key={article.id}
        className={`focus-ring flex min-w-56 shrink-0 items-center justify-between gap-3 rounded-2xl border px-3 py-2.5 text-left text-sm transition ${
          selected
            ? "border-civic bg-civic text-white shadow-sm dark:border-cyan-700 dark:bg-cyan-800"
            : "border-stone-200 bg-stone-50 text-stone-800 hover:border-cyan-300 hover:bg-white hover:shadow-sm dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100 dark:hover:border-cyan-800"
        }`}
        onClick={() => onSelect(article.id)}
      >
        <span className="min-w-0">
          <span className="block truncate font-semibold">{formatSourceName(article.source?.name, article.source?.name_en)}</span>
          <span className={`block truncate text-xs ${selected ? "text-cyan-50/85" : "text-stone-500 dark:text-stone-400"}`}>
            {formatCountry(article.source?.country)} / {formatRegion(article.source?.region)} / {text.originalLanguage}：{formatLanguage(article.language || article.source?.language)}
          </span>
        </span>
        <CredibilityBadge score={article.source?.composite_credibility} />
      </button>
    );
  };

  return (
    <div className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 px-4 py-3 shadow-sm backdrop-blur dark:border-stone-800 dark:bg-stone-950/95">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-civic dark:text-cyan-200">{text.sourceOrder}</span>
          <div className="text-sm text-stone-500 dark:text-stone-400">{articles.length} 个来源可对照阅读</div>
        </div>
        <div className="grid grid-cols-3 rounded-2xl border border-stone-200 bg-stone-50 p-1 text-xs font-semibold dark:border-stone-800 dark:bg-stone-900">
          <button className={`rounded-xl px-2.5 py-1.5 transition ${mode === "readable" ? "bg-white text-civic shadow-sm dark:bg-stone-800 dark:text-cyan-200" : "text-stone-500"}`} onClick={() => setMode("readable")}>
            {text.fullReportsFirst}
          </button>
          <button className={`rounded-xl px-2.5 py-1.5 transition ${mode === "credibility" ? "bg-white text-civic shadow-sm dark:bg-stone-800 dark:text-cyan-200" : "text-stone-500"}`} onClick={() => setMode("credibility")}>
            {text.byCredibility}
          </button>
          <button className={`rounded-xl px-2.5 py-1.5 transition ${mode === "region" ? "bg-white text-civic shadow-sm dark:bg-stone-800 dark:text-cyan-200" : "text-stone-500"}`} onClick={() => setMode("region")}>
            {text.byRegion}
          </button>
        </div>
      </div>
      {mode === "readable" ? (
        <div className="soft-scrollbar mt-3 flex gap-2 overflow-x-auto pb-1">{sortedByReadable.map(renderButton)}</div>
      ) : mode === "credibility" ? (
        <div className="soft-scrollbar mt-3 flex gap-2 overflow-x-auto pb-1">{sortedByCredibility.map(renderButton)}</div>
      ) : (
        <div className="soft-scrollbar mt-3 flex gap-3 overflow-x-auto pb-1">
          {groupedByRegion.map(([region, rows]) => (
            <div key={region} className="flex shrink-0 items-center gap-2 rounded-2xl bg-stone-50 p-2 dark:bg-stone-900/70">
              <span className="px-1 text-xs font-semibold text-stone-500 dark:text-stone-400">{formatRegion(region)}</span>
              {rows.map(renderButton)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
