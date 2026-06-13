import { useState } from "react";
import { formatLanguage, getUiText } from "../../utils/i18n";

type Props = {
  text?: string;
  original?: string;
  originalLanguage?: string;
  className?: string;
};

export function OriginalText({ text, original, originalLanguage = "auto", className }: Props) {
  const labels = getUiText();
  const [showOriginal, setShowOriginal] = useState(false);
  const hasOriginal = Boolean(original?.trim());
  const value = showOriginal && hasOriginal ? original : text;

  return (
    <div>
      <div className={className}>{value}</div>
      {hasOriginal ? (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-stone-500 dark:text-stone-400">
          <span>原文语言：{formatLanguage(originalLanguage)}</span>
          <button
            className="rounded border border-stone-300 px-2 py-1 text-stone-700 hover:border-cyan-400 dark:border-stone-700 dark:text-stone-200"
            onClick={() => setShowOriginal((value) => !value)}
            type="button"
          >
            {showOriginal ? labels.showChinese : labels.original}
          </button>
        </div>
      ) : null}
    </div>
  );
}
