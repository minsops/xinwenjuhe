import axios from "axios";
import type { Article } from "../types/article";
import type { EventAnalysis } from "../types/analysis";
import type { Event } from "../types/event";
import type { Source } from "../types/source";
import type { TaskOverview } from "../types/task";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
});

type Envelope<T> = { data: T; meta?: Record<string, unknown> };

export type EventQuery = {
  region?: string;
  category?: string;
  sort?: "heat" | "latest";
  min_heat?: number;
};

export async function fetchEvents(query: EventQuery = {}): Promise<Event[]> {
  const { data } = await client.get<Envelope<Event[]>>("/api/v1/events", { params: query });
  return data.data;
}

export async function fetchEventArticles(eventId: string): Promise<Article[]> {
  const { data } = await client.get<Envelope<Article[]>>(`/api/v1/events/${eventId}/articles`);
  return data.data;
}

export async function fetchAnalysis(eventId: string): Promise<EventAnalysis> {
  const { data } = await client.get<Envelope<EventAnalysis>>(`/api/v1/events/${eventId}/analysis`);
  return data.data;
}

export async function runEventAnalysis(eventId: string): Promise<EventAnalysis> {
  const { data } = await client.post<Envelope<EventAnalysis>>(`/api/v1/analysis/events/${eventId}/run`);
  return data.data;
}

type TranslationResult = {
  title: string;
  summary?: string;
  content?: string;
  cached: boolean;
  fallback?: boolean;
  message?: string;
};

export async function translateEvent(eventId: string): Promise<TranslationResult & { summary: string }> {
  const { data } = await client.post<Envelope<TranslationResult & { summary: string }>>(`/api/v1/events/${eventId}/translate`);
  return data.data;
}

export async function fetchSources(): Promise<Source[]> {
  const { data } = await client.get<Envelope<Source[]>>("/api/v1/sources");
  return data.data;
}

export async function translateArticle(articleId: string, targetLang: string): Promise<TranslationResult & { content: string }> {
  const { data } = await client.post<Envelope<TranslationResult & { content: string }>>(
    `/api/v1/articles/${articleId}/translate`,
    { target_lang: targetLang }
  );
  return data.data;
}

export async function fetchTaskOverview(): Promise<TaskOverview> {
  const { data } = await client.get<Envelope<TaskOverview>>("/api/v1/tasks");
  return data.data;
}

export async function refreshSourceCredibility(): Promise<{ task_id: string; status: string }> {
  const { data } = await client.post<Envelope<{ task_id: string; status: string }>>("/api/v1/sources/refresh-credibility");
  return data.data;
}

export async function startCollectActiveSources(): Promise<{ task_id: string; status: string }> {
  const { data } = await client.post<Envelope<{ task_id: string; status: string }>>("/api/v1/tasks/collect-active-sources");
  return data.data;
}

export async function startCollectHotEvents(): Promise<{ task_id: string; status: string }> {
  const { data } = await client.post<Envelope<{ task_id: string; status: string }>>("/api/v1/tasks/collect-hot-events");
  return data.data;
}

export async function startBackfillShortArticles(): Promise<{ task_id: string; status: string }> {
  const { data } = await client.post<Envelope<{ task_id: string; status: string }>>("/api/v1/tasks/backfill-short-articles");
  return data.data;
}

export async function startClusterNewArticles(): Promise<{ task_id: string; status: string }> {
  const { data } = await client.post<Envelope<{ task_id: string; status: string }>>("/api/v1/tasks/cluster-new-articles");
  return data.data;
}
