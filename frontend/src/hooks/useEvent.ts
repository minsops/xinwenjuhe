import { useEffect, useState } from "react";
import { fetchEvents, type EventQuery } from "../services/api";
import type { Event } from "../types/event";

export function useEvent(query: EventQuery = {}) {
  const [events, setEvents] = useState<Event[]>([]);
  const [selected, setSelected] = useState<Event | undefined>();

  useEffect(() => {
    fetchEvents(query)
      .then((rows) => {
        setEvents(rows);
        setSelected((current) => rows.find((event) => event.id === current?.id) ?? rows[0]);
      })
      .catch(() => {
        const fallback = demoEvent();
        setEvents([fallback]);
        setSelected(fallback);
      });
  }, [query.region, query.category, query.sort, query.min_heat]);

  return { events, selected, setSelected };
}

function demoEvent(): Event {
  return {
    id: "demo",
    title: "Cross-border incident draws conflicting casualty reports",
    summary: "Multiple outlets report the same incident while disagreeing on numbers and attribution.",
    category: "conflict",
    region_primary: "middle_east",
    status: "active",
    article_count: 3,
    source_count: 3,
    language_count: 2,
    region_count: 3,
    heat_score: 82,
    last_updated_at: new Date().toISOString()
  };
}
