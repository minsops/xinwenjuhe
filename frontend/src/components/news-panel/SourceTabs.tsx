import { useMemo, useState } from "react";
import type { Article } from "../../types/article";
import { formatCountry, formatLanguage, formatRegion, getUiText } from "../../utils/i18n";
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

  const renderButton = (article: Article) => (
    <button
      key={article.id}
      className={`focus-ring flex min-w-48 shrink-0 items-center justify-between gap-3 rounded border px-3 py-2 text-left text-sm ${
        selectedId === article.id ? "bg-civic text-white" : "bg-stone-100 text-stone-800 dark:bg-stone-800 dark:text-stone-100"
      }`}
      onClick={() => onSelect(article.id)}
    >
      <span className="min-w-0">
        <span className="block truncate font-medium">{article.source?.name ?? article.source_id.slice(0, 8)}</span>
        <span className={`block truncate text-xs ${selectedId === article.id ? "text-cyan-50" : "text-stone-500 dark:text-stone-400"}`}>
          {formatCountry(article.source?.country)} / {formatRegion(article.source?.region)} / {text.originalLanguage}：{formatLanguage(article.language || article.source?.language)}
        </span>
      </span>
      <CredibilityBadge score={article.source?.composite_credibility} />
    </button>
  );

  return (
    <div className="border-b border-stone-300 dark:border-stone-700">
      <div className="flex items-center justify-between gap-3 px-3 py-2">
        <span className="text-xs font-medium uppercase text-stone-500 dark:text-stone-400">{text.sourceOrder}</span>
        <div className="grid grid-cols-3 rounded border border-stone-300 p-0.5 text-xs dark:border-stone-700">
          <button className={`rounded px-2 py-1 ${mode === "readable" ? "bg-civic text-white" : ""}`} onClick={() => setMode("readable")}>
            {text.fullReportsFirst}
          </button>
          <button className={`rounded px-2 py-1 ${mode === "credibility" ? "bg-civic text-white" : ""}`} onClick={() => setMode("credibility")}>
            {text.byCredibility}
          </button>
          <button className={`rounded px-2 py-1 ${mode === "region" ? "bg-civic text-white" : ""}`} onClick={() => setMode("region")}>
            {text.byRegion}
          </button>
        </div>
      </div>
      {mode === "readable" ? (
        <div className="flex gap-2 overflow-x-auto px-3 pb-2">{sortedByReadable.map(renderButton)}</div>
      ) : mode === "credibility" ? (
        <div className="flex gap-1 overflow-x-auto px-3 pb-2">{sortedByCredibility.map(renderButton)}</div>
      ) : (
        <div className="flex gap-3 overflow-x-auto px-3 pb-2">
          {groupedByRegion.map(([region, rows]) => (
            <div key={region} className="flex shrink-0 items-center gap-1">
              <span className="mr-1 text-xs text-stone-500 dark:text-stone-400">{formatRegion(region)}</span>
              {rows.map(renderButton)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
