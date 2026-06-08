import type { Source } from "./source";

export type Article = {
  id: string;
  source_id: string;
  external_url: string;
  title_original: string;
  title_translated?: string | null;
  content_original: string;
  content_translated?: string | null;
  language: string;
  published_at?: string | null;
  author?: string | null;
  source?: Source | null;
};

