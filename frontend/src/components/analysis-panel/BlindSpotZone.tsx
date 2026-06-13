import { CircleSlash } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";
import { OriginalText } from "./OriginalText";

type Props = {
  items: EventAnalysis["blind_spots"];
};

export function BlindSpotZone({ items }: Props) {
  const text = getUiText();
  const visibleItems = items.slice(0, 12);
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-3 flex items-center gap-2 font-semibold text-red-800 dark:text-red-300">
        <CircleSlash className="h-4 w-4" />
        {text.blindSpots}
      </div>
      <p className="mb-3 text-xs leading-5 text-stone-500 dark:text-stone-400">{text.blindSpotHelp}</p>
      <div className="space-y-3">
        {visibleItems.length ? visibleItems.map((item, index) => {
          return (
          <div key={`${item.description}-${index}`} className="rounded border border-red-200 bg-red-50 p-3 text-sm dark:border-red-900 dark:bg-red-950">
            <OriginalText text={item.description} original={item.description_original} originalLanguage={item.description_original_language} />
            {item.total ? <div className="mt-2"><Badge tone="red">{item.mentioned_by}/{item.total} 个来源</Badge></div> : null}
          </div>
        );}) : <p className="text-sm text-stone-500">{text.noBlindSpots}</p>}
        {items.length > visibleItems.length ? <p className="text-xs text-stone-500">另有 {items.length - visibleItems.length} 条低覆盖线索已折叠。</p> : null}
      </div>
    </section>
  );
}
