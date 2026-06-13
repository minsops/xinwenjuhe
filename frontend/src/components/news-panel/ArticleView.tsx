import { ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import type { Article } from "../../types/article";
import { formatDate } from "../../utils/formatDate";
import { formatCountry, formatLanguage, formatRegion, formatSourceChineseName, formatSourceOriginalName, getUiText } from "../../utils/i18n";
import { usableChineseText } from "../../utils/chineseText";
import { OriginalText } from "../analysis-panel/OriginalText";
import { CredibilityBadge } from "./CredibilityBadge";
import { TranslateButton } from "./TranslateButton";

type Props = {
  article?: Article;
  showingChinese: boolean;
  loadingTranslation: boolean;
  translatedTitle?: string;
  translatedContent?: string;
  translationError?: string;
  backfillNotice?: string;
  backfillLoading?: boolean;
  highlightedFact?: string;
  onShowChinese: () => void;
  onShowOriginal: () => void;
  onBackfillFulltext?: () => void;
};

export function ArticleView({ article, showingChinese, loadingTranslation, translatedTitle, translatedContent, translationError, backfillNotice, backfillLoading, highlightedFact, onShowChinese, onShowOriginal, onBackfillFulltext }: Props) {
  const text = getUiText();
  if (!article) {
    return <div className="p-6 text-sm text-stone-500">{text.noArticle}</div>;
  }
  const source = article.source;
  const savedChineseTitle = usableChineseText(article.title_translated);
  const savedChineseContent = usableChineseText(article.content_translated);
  const sourceChineseName = formatSourceChineseName(source?.name, source?.name_en);
  const sourceOriginalName = formatSourceOriginalName(source?.name, source?.name_en);
  const title = showingChinese
    ? translatedTitle ?? savedChineseTitle ?? (loadingTranslation ? "正在翻译标题..." : "这篇报道暂时没有可用的中文标题")
    : article.title_original;
  const content = showingChinese
    ? translatedContent ?? savedChineseContent ?? (loadingTranslation ? "正在翻译正文..." : "自动翻译服务暂不可用，系统没有拿到可用的中文正文。你可以点击“显示原文”查看来源原文，原文语言已在文章信息中标注。")
    : article.content_original;
  const isShortContent = article.content_original.trim().length < 180;
  const normalizedFact = highlightedFact?.trim().toLowerCase();
  const paragraphs = articleParagraphs(content);
  const factMatchesParagraph = (paragraph: string) => {
    if (!normalizedFact) return false;
    const normalizedParagraph = paragraph.toLowerCase();
    if (normalizedParagraph.includes(normalizedFact)) return true;
    const tokens = normalizedFact.split(/[^a-z0-9]+/).filter((token) => token.length > 3);
    if (tokens.length < 3) return false;
    const matches = tokens.filter((token) => normalizedParagraph.includes(token)).length;
    return matches >= Math.min(4, Math.ceil(tokens.length * 0.6));
  };
  return (
    <article className="mx-auto max-w-[840px] px-5 py-6 lg:px-7">
      <div className="mb-5 rounded-3xl border border-stone-200 bg-stone-50/80 p-4 shadow-sm dark:border-stone-800 dark:bg-stone-900/50">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-stone-600 dark:text-stone-300">
            <span>{formatDate(article.published_at)}</span>
            {article.author ? <span> · {article.author}</span> : null}
          </div>
          <TranslateButton showingChinese={showingChinese} loading={loadingTranslation} onShowChinese={onShowChinese} onShowOriginal={onShowOriginal} />
        </div>
        <div className="mt-4 inline-flex rounded-full bg-white px-3 py-1 text-xs font-semibold text-civic shadow-sm dark:bg-stone-800 dark:text-cyan-200">
          {showingChinese ? text.translatedVersion : text.originalArticle}
        </div>
        <div className="mt-3 text-xs text-stone-500">{text.originalLanguage}：{formatLanguage(article.language || source?.language)}</div>
        <h2 className="mt-2 text-2xl font-black leading-tight tracking-tight text-stone-950 dark:text-white lg:text-3xl">{title}</h2>
        <div className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <MetaItem label={text.sourceAgency}>
            <OriginalText
              className="font-semibold text-stone-800 dark:text-stone-100"
              text={sourceChineseName}
              original={sourceOriginalName}
              originalLanguage={source?.language || article.language}
            />
          </MetaItem>
          <MetaItem label={text.sourceCountry} value={formatCountry(source?.country)} />
          <MetaItem label={text.sourceRegion} value={formatRegion(source?.region)} />
          <MetaItem label={text.sourceLanguage} value={formatLanguage(article.language || source?.language)} />
          <div className="rounded-2xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-stone-950">
            <div className="text-xs text-stone-500">{text.credibility}</div>
            <div className="mt-1"><CredibilityBadge score={source?.composite_credibility} /></div>
          </div>
          <a className="focus-ring inline-flex items-center justify-center gap-2 rounded-2xl border border-cyan-200 bg-white p-3 font-semibold text-civic transition hover:-translate-y-0.5 hover:shadow-sm dark:border-cyan-900 dark:bg-stone-950 dark:text-cyan-200" href={article.external_url} target="_blank" rel="noreferrer">
            {text.readFullOriginal} <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
      {isShortContent ? (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          <div>{text.shortContentNotice}</div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {onBackfillFulltext ? (
              <button
                className="focus-ring rounded border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 transition hover:border-amber-500 disabled:cursor-wait disabled:opacity-70 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
                disabled={backfillLoading}
                onClick={onBackfillFulltext}
                type="button"
              >
                {backfillLoading ? text.submittingTask : text.backfillThisArticle}
              </button>
            ) : null}
            {backfillNotice ? <span className="text-xs leading-5 text-amber-900 dark:text-amber-100">{backfillNotice}</span> : null}
          </div>
        </div>
      ) : null}
      {translationError ? (
        <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-950 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
          {translationError}
        </div>
      ) : null}
      {highlightedFact ? (
        <div className="mt-4 rounded-2xl border border-civic bg-cyan-50 p-3 text-sm leading-6 text-cyan-950 dark:border-cyan-700 dark:bg-cyan-950 dark:text-cyan-100">
          <div className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-civic dark:text-cyan-200">选中的事实片段</div>
          {highlightedFact}
        </div>
      ) : null}
      <div className="reading-flow mt-6 space-y-5 text-stone-800 dark:text-stone-100">
        {paragraphs.map((paragraph, index) => {
          const highlighted = factMatchesParagraph(paragraph);
          return (
            <p
              key={`${index}-${paragraph.slice(0, 24)}`}
              className={highlighted ? "rounded-2xl border border-civic bg-cyan-50 p-4 text-cyan-950 dark:border-cyan-700 dark:bg-cyan-950 dark:text-cyan-50" : ""}
            >
              {paragraph}
            </p>
          );
        })}
        {!paragraphs.length ? content : null}
      </div>
    </article>
  );
}

function MetaItem({ label, value, children }: { label: string; value?: string; children?: ReactNode }) {
  return (
    <div aria-label={label} className="rounded-2xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-stone-950">
      <div className="text-xs text-stone-500">{label}</div>
      <div className="mt-1 font-semibold text-stone-800 dark:text-stone-100">{children ?? value}</div>
    </div>
  );
}

function articleParagraphs(content: string): string[] {
  const blocks = content.split(/\n{2,}/).map((paragraph) => paragraph.trim()).filter(Boolean);
  if (blocks.length > 1 || content.length < 360) return blocks;
  const sentences = content.match(/[^.!?。！？]+[.!?。！？]+/g);
  if (!sentences || sentences.length < 4) return blocks;
  const paragraphs: string[] = [];
  for (let index = 0; index < sentences.length; index += 3) {
    paragraphs.push(sentences.slice(index, index + 3).join(" ").trim());
  }
  return paragraphs;
}
