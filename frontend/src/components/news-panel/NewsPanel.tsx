import { useEffect, useMemo, useState } from "react";
import type { Article } from "../../types/article";
import { startArticleFulltextBackfill, translateArticle } from "../../services/api";
import { getUiText } from "../../utils/i18n";
import { ArticleView } from "./ArticleView";
import { SourceTabs } from "./SourceTabs";

type Props = {
  articles: Article[];
  hasSelectedEvent?: boolean;
  selectedArticleId?: string;
  highlightedFact?: string;
  onArticleSelect?: (articleId: string) => void;
};

export function NewsPanel({ articles, hasSelectedEvent = true, selectedArticleId, highlightedFact, onArticleSelect }: Props) {
  const text = getUiText();
  const [selectedId, setSelectedId] = useState<string | undefined>(articles[0]?.id);
  const [showingChinese, setShowingChinese] = useState(true);
  const [loading, setLoading] = useState(false);
  const [translationError, setTranslationError] = useState<string | undefined>();
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [backfillNotice, setBackfillNotice] = useState<string | undefined>();
  const [translatedByArticle, setTranslatedByArticle] = useState<Record<string, { title: string; content: string }>>({});

  const readableArticles = useMemo(() => sortReadableArticles(articles), [articles]);
  const selected = useMemo(
    () => readableArticles.find((article) => article.id === selectedId) ?? readableArticles[0],
    [readableArticles, selectedId]
  );
  const translatedText = selected ? translatedByArticle[selected.id] : undefined;

  useEffect(() => {
    if (selectedArticleId) {
      setSelectedId(selectedArticleId);
      setShowingChinese(true);
      setTranslationError(undefined);
      setBackfillNotice(undefined);
    } else if (!selectedId && readableArticles[0]) {
      setSelectedId(readableArticles[0].id);
    }
  }, [readableArticles, selectedArticleId, selectedId]);

  useEffect(() => {
    if (!selected || !showingChinese) return;
    if (isChineseLanguage(selected.language)) {
      setTranslatedByArticle((current) => ({
        ...current,
        [selected.id]: { title: selected.title_original, content: selected.content_original }
      }));
      return;
    }
    if (translatedByArticle[selected.id]) return;
    void loadChinese(selected);
  }, [selected?.id, showingChinese]);

  async function loadChinese(article: Article) {
    setLoading(true);
    setTranslationError(undefined);
    try {
      const result = await translateArticle(article.id, "zh");
      setTranslatedByArticle((current) => ({ ...current, [article.id]: { title: result.title, content: result.content } }));
      if (result.fallback) {
        setTranslationError(result.message ?? "自动翻译暂不可用：当前显示的是中文说明，不是完整译文。");
      }
    } catch {
      setShowingChinese(false);
      setTranslationError("翻译失败：翻译服务没有返回可用的中文。");
    } finally {
      setLoading(false);
    }
  }

  async function handleShowChinese() {
    if (!selected) return;
    setShowingChinese(true);
    if (!translatedByArticle[selected.id]) await loadChinese(selected);
  }

  async function handleBackfillFulltext() {
    if (!selected || backfillLoading) return;
    setBackfillLoading(true);
    setBackfillNotice(undefined);
    try {
      await startArticleFulltextBackfill(selected.id);
      setBackfillNotice(text.backfillArticleQueued);
    } catch {
      setBackfillNotice(text.backfillArticleFailed);
    } finally {
      setBackfillLoading(false);
    }
  }

  return (
    <div className="soft-scrollbar h-full overflow-y-auto bg-white dark:bg-stone-950">
      {articles.length ? (
        <SourceTabs articles={readableArticles} selectedId={selected?.id} onSelect={(id) => { setSelectedId(id); setShowingChinese(true); setTranslationError(undefined); setBackfillNotice(undefined); onArticleSelect?.(id); }} />
      ) : null}
      {!articles.length ? (
        <div className="flex min-h-[420px] items-center justify-center p-6 text-center">
          <div className="max-w-sm">
            <div className="text-lg font-black text-stone-900 dark:text-stone-50">
              {hasSelectedEvent ? text.noArticlesTitle : text.noEventsTitle}
            </div>
            <p className="mt-2 text-sm leading-6 text-stone-500 dark:text-stone-400">
              {hasSelectedEvent ? text.noArticlesDescription : text.noEventSelected}
            </p>
          </div>
        </div>
      ) : null}
      {articles.length ? (
        <ArticleView
          article={selected}
          showingChinese={showingChinese}
          loadingTranslation={loading}
          translatedTitle={translatedText?.title}
          translatedContent={translatedText?.content}
          translationError={translationError}
          backfillNotice={backfillNotice}
          backfillLoading={backfillLoading}
          highlightedFact={highlightedFact}
          onShowChinese={handleShowChinese}
          onShowOriginal={() => { setShowingChinese(false); setTranslationError(undefined); }}
          onBackfillFulltext={handleBackfillFulltext}
        />
      ) : null}
    </div>
  );
}

function isChineseLanguage(language?: string | null): boolean {
  return Boolean(language?.toLowerCase().startsWith("zh"));
}

function sortReadableArticles(articles: Article[]): Article[] {
  return [...articles].sort((left, right) => {
    const score = articleReadabilityScore(right) - articleReadabilityScore(left);
    if (score !== 0) return score;
    return publishedMs(right) - publishedMs(left);
  });
}

function articleReadabilityScore(article: Article): number {
  const contentLength = article.content_original.trim().length;
  let score = Math.min(contentLength, 1200);
  if (contentLength >= 220) score += 500;
  if (article.source?.name && article.source.name !== "news.google.com") score += 350;
  if (article.source?.country && article.source.country !== "Unknown") score += 180;
  if (article.source?.region && article.source.region !== "unknown") score += 120;
  if (article.author) score += 40;
  return score;
}

function publishedMs(article: Article): number {
  return article.published_at ? new Date(article.published_at).getTime() : 0;
}
