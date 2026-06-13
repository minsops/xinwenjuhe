import { Tags } from "lucide-react";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  frames: Array<Record<string, unknown>>;
  sourceLabels?: Record<string, string>;
};

export function NarrativeFrameComparison({ frames, sourceLabels = {} }: Props) {
  const text = getUiText();
  return (
    <section className="p-4">
      <div className="mb-3 flex items-center gap-2 font-semibold text-civic dark:text-cyan-200">
        <Tags className="h-4 w-4" />
        {text.narrativeFrames}
      </div>
      <div className="space-y-2">
        {frames.length ? frames.map((frame, index) => {
          const tags = Array.isArray(frame.frames) ? frame.frames.map((item) => formatFrameLabel(String(item))) : ["一般新闻报道"];
          const sourceId = String(frame.source_id ?? "");
          const sourceName = formatSourceName(sourceId, frame.source_name, sourceLabels, index);
          return (
            <details key={index} open={index < 2} className="rounded border border-stone-200 p-3 text-sm dark:border-stone-700">
              <summary className="cursor-pointer">{sourceName}</summary>
              <div className="mt-2 flex flex-wrap gap-2">{tags.map((tag) => <Badge key={tag} tone="blue">{tag}</Badge>)}</div>
              {frame.angle ? <div className="mt-2 text-stone-600 dark:text-stone-300">角度：{formatFrameLabel(String(frame.angle))}</div> : null}
              {frame.tone ? <div className="mt-1 text-stone-600 dark:text-stone-300">基调：{formatFrameLabel(String(frame.tone))}</div> : null}
            </details>
          );
        }) : <p className="text-sm text-stone-500">{text.noFrames}</p>}
      </div>
    </section>
  );
}

function formatFrameLabel(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/-/g, "_");
  const labels: Record<string, string> = {
    news_report: "一般新闻报道",
    "factual report": "事实报道",
    factual_report: "事实报道",
    neutral: "中性",
    critical: "批评",
    conflict: "冲突",
    alleged: "指称",
    official_statement: "官方表述",
    security: "安全事件",
    security_incident: "安全事件",
    attack: "袭击叙事",
    responsibility: "责任归属",
    external_responsibility: "外部责任",
    official_claims: "官方说法",
    official_uncertainty: "官方不确定性",
    "strong attribution": "强烈归责",
    strong_attribution: "强烈归责",
    humanitarian: "人道影响",
    casualties: "伤亡规模",
    casualty_claim: "伤亡主张",
    verification_gap: "核验不足",
    regional_tension: "地区紧张",
    victim_frame: "受害者叙事",
    aggressor_frame: "加害者叙事",
    accountability: "追责叙事"
  };
  if (labels[normalized]) return labels[normalized];
  if (normalized.includes("_")) return normalized.split("_").join(" ");
  return value;
}

function formatSourceName(
  sourceId: string,
  sourceName: unknown,
  sourceLabels: Record<string, string>,
  index: number,
): string {
  if (sourceId && sourceLabels[sourceId]) return sourceLabels[sourceId];
  if (typeof sourceName === "string" && sourceName.trim() && !isUuidLike(sourceName)) return sourceName;
  if (sourceId && !isUuidLike(sourceId)) return sourceId;
  return `来源 ${index + 1}`;
}

function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.trim());
}
