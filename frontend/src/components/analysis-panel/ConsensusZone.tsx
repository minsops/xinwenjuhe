import { CheckCircle2 } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";
import { OriginalText } from "./OriginalText";

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
          <div
            key={item.fact}
            className="rounded border border-green-200 bg-green-50 p-3 text-sm dark:border-green-900 dark:bg-green-950"
          >
            <OriginalText text={item.fact} original={item.fact_original} originalLanguage={item.fact_original_language} />
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone="green">{item.confirmed_by}/{item.total} 个独立来源</Badge>
              {item.syndicated_count ? <Badge tone="yellow">含 {item.syndicated_count} 篇通讯社转载</Badge> : null}
            </div>
            {item.article_ids?.[0] ? (
              <button
                className="focus-ring mt-3 rounded border border-green-300 bg-white px-2 py-1 text-xs font-semibold text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200"
                onClick={() => onFactSelect?.(item.article_ids![0], item.fact)}
                type="button"
              >
                查看对应报道：{item.fact}
              </button>
            ) : null}
          </div>
        )) : <p className="text-sm text-stone-500">{text.noConsensus}</p>}
      </div>
    </section>
  );
}
