import { Tags } from "lucide-react";
import { getUiText } from "../../utils/i18n";
import { Badge } from "../shared/Badge";

type Props = {
  frames: Array<Record<string, unknown>>;
};

export function NarrativeFrameComparison({ frames }: Props) {
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
          return (
            <details key={index} className="rounded border border-stone-200 p-3 text-sm dark:border-stone-700">
              <summary className="cursor-pointer">{String(frame.source_id ?? `Source ${index + 1}`)}</summary>
              <div className="mt-2 flex flex-wrap gap-2">{tags.map((tag) => <Badge key={tag} tone="blue">{tag}</Badge>)}</div>
            </details>
          );
        }) : <p className="text-sm text-stone-500">{text.noFrames}</p>}
      </div>
    </section>
  );
}
