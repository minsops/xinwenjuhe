import { ExternalLink } from "lucide-react";
import type { Article } from "../../types/article";
import { formatDate } from "../../utils/formatDate";
import { formatCountry, formatLanguage, formatRegion, getUiText } from "../../utils/i18n";
import { CredibilityBadge } from "./CredibilityBadge";
import { TranslateButton } from "./TranslateButton";

type Props = {
  article?: Article;
  showingChinese: boolean;
  loadingTranslation: boolean;
  translatedTitle?: string;
  translatedContent?: string;
  translationError?: string;
  highlightedFact?: string;
  onShowChinese: () => void;
  onShowOriginal: () => void;
};

export function ArticleView({ article, showingChinese, loadingTranslation, translatedTitle, translatedContent, translationError, highlightedFact, onShowChinese, onShowOriginal }: Props) {
  const text = getUiText();
  if (!article) {
    return <div className="p-6 text-sm text-stone-500">{text.noArticle}</div>;
  }
  const title = showingChinese
    ? translatedTitle ?? article.title_translated ?? (loadingTranslation ? "正在翻译标题..." : article.title_original)
    : article.title_original;
  const content = showingChinese
    ? translatedContent ?? article.content_translated ?? (loadingTranslation ? "正在翻译正文..." : article.content_original)
    : article.content_original;
  const source = article.source;
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
    <article className="mx-auto max-w-3xl px-5 py-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-stone-600 dark:text-stone-300">
          <span>{formatDate(article.published_at)}</span>
          {article.author ? <span> · {article.author}</span> : null}
        </div>
        <TranslateButton showingChinese={showingChinese} loading={loadingTranslation} onShowChinese={onShowChinese} onShowOriginal={onShowOriginal} />
      </div>
      <div className="mb-3 inline-flex rounded bg-stone-100 px-2 py-1 text-xs font-medium text-stone-700 dark:bg-stone-800 dark:text-stone-200">
        {showingChinese ? text.translatedVersion : text.originalArticle}
      </div>
      <div className="mb-3 text-xs text-stone-500">{text.originalLanguage}：{formatLanguage(article.language || source?.language)}</div>
      <h2 className="text-2xl font-semibold leading-tight">{title}</h2>
      <div className="mt-4 grid gap-3 rounded border border-stone-200 bg-stone-50 p-3 text-sm dark:border-stone-700 dark:bg-stone-900 sm:grid-cols-2">
        <MetaItem label={text.sourceAgency} value={source?.name_en && source.name_en !== source.name ? `${source.name} / ${source.name_en}` : source?.name ?? text.unknown} />
        <MetaItem label={text.sourceCountry} value={formatCountry(source?.country)} />
        <MetaItem label={text.sourceRegion} value={formatRegion(source?.region)} />
        <MetaItem label={text.sourceLanguage} value={formatLanguage(article.language || source?.language)} />
        <div>
          <div className="text-xs text-stone-500">{text.credibility}</div>
          <CredibilityBadge score={source?.composite_credibility} />
        </div>
        <a className="inline-flex items-center gap-1 text-civic dark:text-cyan-200" href={article.external_url} target="_blank" rel="noreferrer">
          {text.readFullOriginal} <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>
      {isShortContent ? (
        <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          {text.shortContentNotice}
        </div>
      ) : null}
      {translationError ? (
        <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-950 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
          {translationError}
        </div>
      ) : null}
      {highlightedFact ? (
        <div className="mt-4 rounded border border-civic bg-cyan-50 p-3 text-sm text-cyan-950 dark:border-cyan-700 dark:bg-cyan-950 dark:text-cyan-100">
          {highlightedFact}
        </div>
      ) : null}
      <div className="mt-5 space-y-4 text-base leading-7 text-stone-800 dark:text-stone-100">
        {paragraphs.map((paragraph, index) => {
          const highlighted = factMatchesParagraph(paragraph);
          return (
            <p
              key={`${index}-${paragraph.slice(0, 24)}`}
              className={highlighted ? "rounded border border-civic bg-cyan-50 p-3 text-cyan-950 dark:border-cyan-700 dark:bg-cyan-950 dark:text-cyan-50" : ""}
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

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-stone-500">{label}</div>
      <div className="font-medium text-stone-800 dark:text-stone-100">{value}</div>
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
