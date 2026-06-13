export type Event = {
  id: string;
  title: string;
  title_en?: string | null;
  title_zh?: string;
  summary_zh?: string;
  translation_error?: string;
  summary?: string | null;
  category?: string | null;
  region_primary?: string | null;
  status: string;
  article_count: number;
  source_count: number;
  language_count: number;
  region_count: number;
  heat_score: number;
  last_updated_at?: string | null;
};
