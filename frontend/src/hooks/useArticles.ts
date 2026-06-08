import { useEffect, useState } from "react";
import { fetchEventArticles } from "../services/api";
import type { Article } from "../types/article";

export function useArticles(eventId?: string) {
  const [articles, setArticles] = useState<Article[]>([]);

  useEffect(() => {
    if (!eventId) return;
    if (eventId === "demo") {
      setArticles(demoArticles());
      return;
    }
    fetchEventArticles(eventId).then(setArticles).catch(() => setArticles(demoArticles()));
  }, [eventId]);

  return articles;
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
