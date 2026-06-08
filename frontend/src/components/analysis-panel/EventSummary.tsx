import { FileText } from "lucide-react";
import { formatMessage, getUiText } from "../../utils/i18n";

type Props = {
  summary: string;
  count: number;
};

export function EventSummary({ summary, count }: Props) {
  const text = getUiText();
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-civic dark:text-cyan-200">
        <FileText className="h-4 w-4" />
        {text.summary}
      </div>
      <p className="text-sm leading-6">{summary}</p>
      <div className="mt-2 text-xs text-stone-500">{formatMessage(text.basedOnReports, { count })}</div>
    </section>
  );
}
