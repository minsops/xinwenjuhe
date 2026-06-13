import { useEffect, useState } from "react";
import { fetchEventArticles } from "../services/api";
import type { Article } from "../types/article";

export function useArticles(eventId?: string) {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    let active = true;
    if (!eventId) {
      setArticles([]);
      return () => {
        active = false;
      };
    }
    setArticles([]);
    if (eventId === "demo") {
      setArticles(demoArticles());
      return () => {
        active = false;
      };
    }
    fetchEventArticles(eventId)
      .then((rows) => {
        if (active) setArticles(sortReadableArticles(rows));
      })
      .catch(() => {
        if (active) setArticles(demoArticles());
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  return articles;
}

function sortReadableArticles(articles: Article[]): Article[] {
  return [...articles].sort((left, right) => articleReadabilityScore(right) - articleReadabilityScore(left) || publishedMs(right) - publishedMs(left));
}

function articleReadabilityScore(article: Article): number {
  const source = article.source;
  const contentLength = article.content_original.trim().length;
  let score = Math.min(contentLength, 1200);
  if (contentLength >= 220) score += 500;
  if (source?.name && source.name !== "news.google.com") score += 350;
  if (source?.country && source.country !== "Unknown") score += 180;
  if (source?.region && source.region !== "unknown") score += 120;
  if (article.author) score += 40;
  return score;
}

function publishedMs(article: Article): number {
  return article.published_at ? new Date(article.published_at).getTime() : 0;
}

function demoArticles(): Article[] {
  return [
    {
      id: "a1",
      source_id: "reuters",
      external_url: "https://example.com/reuters",
      title_original: "Officials report 12 casualties after overnight strike",
      content_original: "An overnight incident occurred and local authorities responded.\n\nOfficials said 12 people were killed after an overnight strike. The cause remains under investigation, according to local authorities.",
      language: "en",
      published_at: new Date().toISOString(),
      source: { id: "reuters", name: "Reuters", country: "United Kingdom", region: "europe", language: "en", composite_credibility: 86 }
    },
    {
      id: "a2",
      source_id: "irna",
      external_url: "https://example.com/irna",
      title_original: "Local agency says more than 200 affected in attack",
      content_original: "The agency reported more than 200 people affected and attributed responsibility to foreign forces, citing an official statement.",
      language: "en",
      published_at: new Date().toISOString(),
      source: { id: "irna", name: "IRNA", country: "Iran", region: "middle_east", language: "en", composite_credibility: 48 }
    }
  ];
}
