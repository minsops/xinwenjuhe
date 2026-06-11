import { CircleSlash } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  items: EventAnalysis["blind_spots"];
};

export function BlindSpotZone({ items }: Props) {
  const text = getUiText();
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-3 flex items-center gap-2 font-semibold text-red-800 dark:text-red-300">
        <CircleSlash className="h-4 w-4" />
        {text.blindSpots}
      </div>
      <div className="space-y-3">
        {items.length ? items.map((item) => (
          <div key={item.description} className="rounded border border-red-200 bg-red-50 p-3 text-sm dark:border-red-900 dark:bg-red-950">
            <div>{item.description}</div>
            {item.total ? <div className="mt-2"><Badge tone="red">{item.mentioned_by}/{item.total} 个来源</Badge></div> : null}
          </div>
        )) : <p className="text-sm text-stone-500">{text.noBlindSpots}</p>}
      </div>
    </section>
  );
}
