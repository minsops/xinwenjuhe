import { Languages, RotateCcw } from "lucide-react";
import { getUiText } from "../../utils/i18n";

type Props = {
  translated: boolean;
  loading: boolean;
  onTranslate: () => void;
  onReset: () => void;
};

export function TranslateButton({ translated, loading, onTranslate, onReset }: Props) {
  const text = getUiText();
  return translated ? (
    <button className="focus-ring inline-flex items-center gap-2 rounded bg-stone-200 px-3 py-2 text-sm" onClick={onReset}>
      <RotateCcw className="h-4 w-4" />
      {text.original}
    </button>
  ) : (
    <button className="focus-ring inline-flex items-center gap-2 rounded bg-civic px-3 py-2 text-sm text-white disabled:opacity-60" onClick={onTranslate} disabled={loading}>
      <Languages className="h-4 w-4" />
      {loading ? text.translating : text.translate}
    </button>
  );
}
