export type EventAnalysis = {
  id?: string;
  event_id: string;
  summary: string;
  analysis_version?: number;
  article_count_at_analysis?: number;
  consensus_facts: Array<{ fact: string; confirmed_by: number; total: number; article_ids?: string[]; source_ids?: string[] }>;
  disputed_facts: Array<{ topic: string; type?: string; severity?: string; details?: unknown }>;
  blind_spots: Array<{ description: string; mentioned_by?: number; total?: number }>;
  narrative_frames: Array<Record<string, unknown>>;
  timeline?: Array<{
    timestamp?: string;
    fact?: string;
    fragment_type?: string;
    article_id?: string;
    source_id?: string;
  }>;
  source_graph?: {
    nodes?: Array<{ id: string; type?: string; severity?: string }>;
    edges?: Array<{ from: string; to: string; type?: string; severity?: string; fragment_type?: string }>;
  };
};
