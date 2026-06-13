import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";

type Props = {
  graph?: EventAnalysis["source_graph"];
  sourceLabels?: Record<string, string>;
};

export function SourceGraph({ graph, sourceLabels = {} }: Props) {
  const text = getUiText();
  const nodes = graph?.nodes ?? [];
  const edges = graph?.edges ?? [];
  const sources = nodes.filter((node) => node.type === "source").slice(0, 12);
  const reported = edges.filter((edge) => edge.type === "reported").length;
  const conflicts = edges.length - reported;

  return (
    <section className="border-t border-stone-200 p-4 dark:border-stone-800">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">{text.sourceGraph}</h2>
      {sources.length === 0 && edges.length === 0 ? (
        <p className="text-sm text-stone-500">{text.noSourceGraph}</p>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded border border-stone-300 bg-white p-2 dark:border-stone-700 dark:bg-stone-950">
              <p className="text-lg font-semibold">{sources.length}</p>
              <p className="text-stone-500">{text.sources}</p>
            </div>
            <div className="rounded border border-stone-300 bg-white p-2 dark:border-stone-700 dark:bg-stone-950">
              <p className="text-lg font-semibold">{reported}</p>
              <p className="text-stone-500">{text.reportedLinks}</p>
            </div>
            <div className="rounded border border-stone-300 bg-white p-2 dark:border-stone-700 dark:bg-stone-950">
              <p className="text-lg font-semibold">{conflicts}</p>
              <p className="text-stone-500">{text.conflictLinks}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {sources.map((source) => (
              <span key={source.id} className="max-w-full truncate rounded border border-civic/30 bg-civic/10 px-2 py-1 text-xs text-civic dark:text-cyan-200">
                {formatSourceNode(source, sourceLabels)}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function formatSourceNode(
  source: { id: string; label?: string; name?: string },
  sourceLabels: Record<string, string>,
): string {
  if (sourceLabels[source.id]) return sourceLabels[source.id];
  if (source.label && !isUuidLike(source.label)) return source.label;
  if (source.name && !isUuidLike(source.name)) return source.name;
  if (!isUuidLike(source.id)) return source.id;
  return "未知来源";
}

function isUuidLike(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.trim());
}
