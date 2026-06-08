import { AlertTriangle } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  items: EventAnalysis["disputed_facts"];
};

export function DisputeZone({ items }: Props) {
  const text = getUiText();
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-3 flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-300">
        <AlertTriangle className="h-4 w-4" />
        {text.disputes}
      </div>
      <div className="space-y-3">
        {items.length ? items.map((item) => (
          <div key={item.topic} className="rounded border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950">
            <div>{item.topic}</div>
            <div className="mt-2 flex gap-2">
              {item.type ? <Badge tone="yellow">{item.type}</Badge> : null}
              {item.severity ? <Badge tone="red">{item.severity}</Badge> : null}
            </div>
          </div>
        )) : <p className="text-sm text-stone-500">{text.noDisputes}</p>}
      </div>
    </section>
  );
}
