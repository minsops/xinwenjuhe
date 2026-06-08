export type Event = {
  id: string;
  title: string;
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

