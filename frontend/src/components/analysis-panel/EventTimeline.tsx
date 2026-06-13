import type { EventAnalysis } from "../../types/analysis";
import { getUiText } from "../../utils/i18n";
import { OriginalText } from "./OriginalText";

type Props = {
  items?: EventAnalysis["timeline"];
};

export function EventTimeline({ items = [] }: Props) {
  const text = getUiText();
  const visible = items.filter((item) => item.timestamp || item.fact).slice(0, 8);

  return (
    <section className="border-t border-stone-200 p-4 dark:border-stone-800">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">{text.timeline}</h2>
      {visible.length === 0 ? (
        <p className="text-sm text-stone-500">{text.noTimeline}</p>
      ) : (
        <ol className="space-y-3">
          {visible.map((item, index) => (
            <li key={`${item.timestamp ?? "untimed"}-${index}`} className="grid grid-cols-[7rem_1fr] gap-3 text-sm">
              <time className="text-xs text-stone-500">
                {item.timestamp ? new Date(item.timestamp).toLocaleString("zh-CN", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "--"}
              </time>
              <div className="border-l border-stone-300 pl-3 dark:border-stone-700">
                <OriginalText
                  className="leading-6 text-stone-800 dark:text-stone-100"
                  text={item.fact}
                  original={item.fact_original}
                  originalLanguage={item.fact_original_language}
                />
                {item.fragment_type ? <p className="mt-1 text-xs text-stone-500">{formatFragmentType(item.fragment_type)}</p> : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function formatFragmentType(type: string): string {
  const labels: Record<string, string> = {
    what: "事件事实",
    who: "相关人物/机构",
    where: "地点",
    when: "时间",
    number: "数字",
    cause: "原因",
    consequence: "影响"
  };
  return labels[type] ?? type;
}
