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
          const tags = Array.isArray(frame.frames) ? frame.frames.map(String) : ["news_report"];
          const sourceId = String(frame.source_id ?? "");
          const sourceName = sourceLabels[sourceId] ?? String(frame.source_name ?? frame.source_id ?? `来源 ${index + 1}`);
          return (
            <details key={index} className="rounded border border-stone-200 p-3 text-sm dark:border-stone-700">
              <summary className="cursor-pointer">{sourceName}</summary>
              <div className="mt-2 flex flex-wrap gap-2">{tags.map((tag) => <Badge key={tag} tone="blue">{tag}</Badge>)}</div>
            </details>
          );
        }) : <p className="text-sm text-stone-500">{text.noFrames}</p>}
      </div>
    </section>
  );
}
