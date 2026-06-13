import { FileText } from "lucide-react";
import { formatMessage, getUiText } from "../../utils/i18n";
import { OriginalText } from "./OriginalText";

type Props = {
  summary: string;
  summaryOriginal?: string;
  summaryOriginalLanguage?: string;
  count: number;
};

export function EventSummary({ summary, summaryOriginal, summaryOriginalLanguage, count }: Props) {
  const text = getUiText();
  return (
    <section className="border-b border-stone-300 p-4 dark:border-stone-700">
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-civic dark:text-cyan-200">
        <FileText className="h-4 w-4" />
        {text.summary}
      </div>
      <OriginalText
        className="text-sm leading-6"
        text={summary}
        original={summaryOriginal}
        originalLanguage={summaryOriginalLanguage}
      />
      <div className="mt-2 text-xs text-stone-500">{formatMessage(text.basedOnReports, { count })}</div>
    </section>
  );
}
