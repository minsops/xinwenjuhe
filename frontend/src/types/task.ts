export type TaskProgress = {
  task_id: string;
  status?: string;
  step?: string;
  event_id?: string;
  updated_at?: string;
  result?: unknown;
};

export type TaskOverview = {
  history: TaskProgress[];
  queue_depth: number | null;
};

