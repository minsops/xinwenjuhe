import { CheckCircle2 } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  items: EventAnalysis["consensus_facts"];
  onFactSelect?: (articleId: string, fact: string) => void;
};

export function ConsensusZone({ items, onFactSelect }: Props) {
  const text = getUiText();
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-3 flex items-center gap-2 font-semibold text-green-800 dark:text-green-300">
        <CheckCircle2 className="h-4 w-4" />
        {text.consensus}
      </div>
      <div className="space-y-3">
        {items.length ? items.map((item) => (
          <button
            key={item.fact}
            className="focus-ring block w-full rounded border border-green-200 bg-green-50 p-3 text-left text-sm dark:border-green-900 dark:bg-green-950"
            onClick={() => item.article_ids?.[0] ? onFactSelect?.(item.article_ids[0], item.fact) : undefined}
          >
            <div>{item.fact}</div>
            <div className="mt-2"><Badge tone="green">{item.confirmed_by}/{item.total} 个来源</Badge></div>
          </button>
        )) : <p className="text-sm text-stone-500">{text.noConsensus}</p>}
      </div>
    </section>
  );
}
