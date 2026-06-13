import { Languages, RotateCcw } from "lucide-react";
import { getUiText } from "../../utils/i18n";

type Props = {
  showingChinese: boolean;
  loading: boolean;
  onShowChinese: () => void;
  onShowOriginal: () => void;
};

export function TranslateButton({ showingChinese, loading, onShowChinese, onShowOriginal }: Props) {
  const text = getUiText();
  if (loading) {
    return (
      <button aria-label={text.translating} className="focus-ring inline-flex items-center gap-2 rounded bg-civic px-3 py-2 text-sm text-white opacity-80" disabled title={text.translating} type="button">
        <Languages className="h-4 w-4" />
        {text.translating}
      </button>
    );
  }
  return showingChinese ? (
    <button aria-label={text.original} className="focus-ring inline-flex items-center gap-2 rounded bg-stone-200 px-3 py-2 text-sm dark:bg-stone-800" onClick={onShowOriginal} title={text.original} type="button">
      <RotateCcw className="h-4 w-4" />
      {text.original}
    </button>
  ) : (
    <button aria-label={text.showChinese} className="focus-ring inline-flex items-center gap-2 rounded bg-civic px-3 py-2 text-sm text-white disabled:opacity-60" onClick={onShowChinese} disabled={loading} title={text.showChinese} type="button">
      <Languages className="h-4 w-4" />
      {loading ? text.translating : text.showChinese}
    </button>
  );
}
