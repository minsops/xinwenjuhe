import { useEffect, useMemo, useState } from "react";
import type { Article } from "../../types/article";
import { translateArticle } from "../../services/api";
import { Skeleton } from "../shared/Skeleton";
import { ArticleView } from "./ArticleView";
import { SourceTabs } from "./SourceTabs";

type Props = {
  articles: Article[];
  selectedArticleId?: string;
  highlightedFact?: string;
  onArticleSelect?: (articleId: string) => void;
};

export function NewsPanel({ articles, selectedArticleId, highlightedFact, onArticleSelect }: Props) {
  const [selectedId, setSelectedId] = useState<string | undefined>(articles[0]?.id);
  const [translated, setTranslated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [translatedText, setTranslatedText] = useState<{ title: string; content: string } | undefined>();

  const selected = useMemo(() => articles.find((article) => article.id === selectedId) ?? articles[0], [articles, selectedId]);

  useEffect(() => {
    if (selectedArticleId) {
      setSelectedId(selectedArticleId);
      setTranslated(false);
    } else if (!selectedId && articles[0]) {
      setSelectedId(articles[0].id);
    }
  }, [articles, selectedArticleId, selectedId]);

  async function handleTranslate() {
    if (!selected) return;
    setLoading(true);
    try {
      const result = await translateArticle(selected.id, "zh");
      setTranslatedText({ title: result.title, content: result.content });
      setTranslated(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-full bg-white dark:bg-stone-950">
      {articles.length ? (
        <SourceTabs articles={articles} selectedId={selected?.id} onSelect={(id) => { setSelectedId(id); setTranslated(false); onArticleSelect?.(id); }} />
      ) : null}
      {!articles.length ? <Skeleton lines={8} /> : null}
      <ArticleView
        article={selected}
        translated={translated}
        loading={loading}
        translatedTitle={translatedText?.title}
        translatedContent={translatedText?.content}
        highlightedFact={highlightedFact}
        onTranslate={handleTranslate}
        onReset={() => setTranslated(false)}
      />
    </div>
  );
}
