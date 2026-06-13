import { AlertTriangle } from "lucide-react";
import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";
import { OriginalText } from "./OriginalText";

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
            <OriginalText text={item.topic} original={item.topic_original} originalLanguage={item.topic_original_language} />
            <div className="mt-2 flex gap-2">
              {item.type ? <Badge tone="yellow">{formatDisputeType(item.type)}</Badge> : null}
              {item.severity ? <Badge tone="red">{formatSeverity(item.severity)}</Badge> : null}
            </div>
          </div>
        )) : <p className="text-sm text-stone-500">{text.noDisputes}</p>}
      </div>
    </section>
  );
}

function formatDisputeType(type: string): string {
  const normalized = type.trim().toLowerCase().replace(/[-\s]+/g, "_");
  const labels: Record<string, string> = {
    number_discrepancy: "数字不一致",
    attribution_conflict: "责任归属冲突",
    timeline_conflict: "时间线冲突",
    omission: "信息遗漏",
    framing_difference: "叙事框架差异"
  };
  return labels[normalized] ?? "其他争议";
}

function formatSeverity(severity: string): string {
  const normalized = severity.trim().toLowerCase();
  const labels: Record<string, string> = {
    critical: "严重",
    high: "高",
    medium: "中",
    low: "低"
  };
  return labels[normalized] ?? "未知级别";
}
