import { useEffect, useState } from "react";
import { fetchTaskOverview } from "../services/api";
import type { TaskOverview } from "../types/task";

export function useTaskProgress() {
  const [overview, setOverview] = useState<TaskOverview>({ history: [], queue_depth: null });

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const data = await fetchTaskOverview();
        if (active) setOverview(data);
      } catch {
        if (active) setOverview({ history: [], queue_depth: null });
      }
    }
    load();
    const timer = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return overview;
}

