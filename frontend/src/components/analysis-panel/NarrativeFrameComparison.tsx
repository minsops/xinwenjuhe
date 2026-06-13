import { Tags } from "lucide-react";
import { formatSourceChineseName, getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";
import { OriginalText } from "./OriginalText";

type Props = {
  frames: Array<Record<string, unknown>>;
  sourceLabels?: Record<string, string>;
};

export function NarrativeFrameComparison({ frames, sourceLabels = {} }: Props) {
  const text = getUiText();
  return (
    <section className="p-4" aria-label={text.narrativeFrames}>
      <div className="mb-3 flex items-center gap-2 font-semibold text-civic dark:text-cyan-200">
        <Tags className="h-4 w-4" />
        {text.narrativeFrames}
      </div>
      <div className="space-y-2">
        {frames.length ? frames.map((frame, index) => {
          const rawTags = valueList(frame.frames);
          const tags = rawTags.length ? rawTags.map((item) => formatFrameLabel(item)) : ["一般新闻报道"];
          const sourceId = String(frame.source_id ?? "");
          const sourceName = formatNarrativeSourceName(sourceId, frame.source_name, sourceLabels, index);
          const framesOriginal = originalListText(frame.frames_original, rawTags, tags);
          const angle = frame.angle ? formatFrameLabel(String(frame.angle)) : "";
          const angleOriginal = originalText(frame.angle_original, frame.angle, angle);
          const tone = frame.tone ? formatFrameLabel(String(frame.tone)) : "";
          const toneOriginal = originalText(frame.tone_original, frame.tone, tone);
          return (
            <details key={index} open={index < 2} className="rounded border border-stone-200 p-3 text-sm dark:border-stone-700">
              <summary className="cursor-pointer">{sourceName}</summary>
              <div className="mt-2 flex flex-wrap gap-2">{tags.map((tag) => <Badge key={tag} tone="blue">{tag}</Badge>)}</div>
              <FrameField
                label="框架"
                value={tags.join("、")}
                original={framesOriginal}
                originalLanguage={String(frame.frames_original_language ?? "auto")}
              />
              {angle ? (
                <FrameField
                  label="角度"
                  value={angle}
                  original={angleOriginal}
                  originalLanguage={String(frame.angle_original_language ?? "auto")}
                />
              ) : null}
              {tone ? (
                <FrameField
                  label="基调"
                  value={tone}
                  original={toneOriginal}
                  originalLanguage={String(frame.tone_original_language ?? "auto")}
                />
              ) : null}
              <FrameField
                label="强调点"
                value={listText(frame.emphasis)}
                original={listText(frame.emphasis_original)}
                originalLanguage={String(frame.emphasis_original_language ?? "auto")}
              />
              <FrameField
                label="淡化点"
                value={listText(frame.downplayed)}
                original={listText(frame.downplayed_original)}
                originalLanguage={String(frame.downplayed_original_language ?? "auto")}
              />
              <FrameField
                label="关键措辞"
                value={listText(frame.wording)}
                original={listText(frame.wording_original)}
                originalLanguage={String(frame.wording_original_language ?? "auto")}
              />
            </details>
          );
        }) : <p className="text-sm text-stone-500">{text.noFrames}</p>}
      </div>
    </section>
  );
}

function FrameField({ label, value, original, originalLanguage }: { label: string; value?: string; original?: string; originalLanguage: string }) {
  if (!value) return null;
  return (
    <div className="mt-2 text-stone-600 dark:text-stone-300">
      <span className="font-medium text-stone-700 dark:text-stone-200">{label}：</span>
      <OriginalText
        className="mt-1 inline leading-6"
        text={value}
        original={original}
        originalLanguage={originalLanguage}
      />
    </div>
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
  if (normalized.includes("_")) return "其他框架";
  if (/[a-z]/i.test(value)) return "其他框架";
  return value;
}

function formatNarrativeSourceName(
  sourceId: string,
  sourceName: unknown,
  sourceLabels: Record<string, string>,
  index: number,
): string {
  if (sourceId && sourceLabels[sourceId]) return sourceLabels[sourceId];
  if (typeof sourceName === "string" && sourceName.trim() && !isUuidLike(sourceName)) return formatSourceChineseName(sourceName);
  if (sourceId && !isUuidLike(sourceId)) return formatSourceChineseName(sourceId);
  return `来源 ${index + 1}`;
}

function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.trim());
}

function valueList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

function listText(value: unknown): string | undefined {
  const values = valueList(value);
  return values.length ? values.join("、") : undefined;
}

function originalListText(original: unknown, rawValues: string[], formattedValues: string[]): string | undefined {
  const explicit = listText(original);
  if (explicit) return explicit;
  const changedRaw = rawValues.filter((value, index) => value !== formattedValues[index] && /[a-z]/i.test(value));
  return changedRaw.length ? changedRaw.join("、") : undefined;
}

function originalText(original: unknown, raw: unknown, formatted: string): string | undefined {
  if (typeof original === "string" && original.trim()) return original.trim();
  if (typeof raw !== "string") return undefined;
  const value = raw.trim();
  if (value && value !== formatted && /[a-z]/i.test(value)) return value;
  return undefined;
}
