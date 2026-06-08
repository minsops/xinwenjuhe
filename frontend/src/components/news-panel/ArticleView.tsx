import { ExternalLink } from "lucide-react";
import type { Article } from "../../types/article";
import { formatDate } from "../../utils/formatDate";
import { getUiText } from "../../utils/i18n";
import { TranslateButton } from "./TranslateButton";

type Props = {
  article?: Article;
  translated: boolean;
  loading: boolean;
  translatedTitle?: string;
  translatedContent?: string;
  highlightedFact?: string;
  onTranslate: () => void;
  onReset: () => void;
};

export function ArticleView({ article, translated, loading, translatedTitle, translatedContent, highlightedFact, onTranslate, onReset }: Props) {
  const text = getUiText();
  if (!article) {
    return <div className="p-6 text-sm text-stone-500">{text.noArticle}</div>;
  }
  const title = translated ? translatedTitle ?? article.title_original : article.title_original;
  const content = translated ? translatedContent ?? article.content_original : article.content_original;
  const normalizedFact = highlightedFact?.trim().toLowerCase();
  const paragraphs = content.split(/\n{2,}/).filter((paragraph) => paragraph.trim().length);
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
        <TranslateButton translated={translated} loading={loading} onTranslate={onTranslate} onReset={onReset} />
      </div>
      <h2 className="text-2xl font-semibold leading-tight">{title}</h2>
      <a className="mt-3 inline-flex items-center gap-1 text-sm text-civic dark:text-cyan-200" href={article.external_url} target="_blank" rel="noreferrer">
        {text.source} <ExternalLink className="h-3.5 w-3.5" />
      </a>
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
