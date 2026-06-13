import { useEffect, useState } from "react";
import { fetchEvents, translateEvent, type EventQuery } from "../services/api";
import type { Event } from "../types/event";

export function useEvent(query: EventQuery = {}) {
  const [events, setEvents] = useState<Event[]>([]);
  const [selected, setSelected] = useState<Event | undefined>();
  const queryKey = JSON.stringify(query);

  useEffect(() => {
    let active = true;
    fetchEvents(query)
      .then((rows) => {
        if (!active) return;
        const pendingRows = rows.map(prepareEventForChineseDisplay);
        setEvents(pendingRows);
        setSelected((current) => pendingRows.find((event) => event.id === current?.id) ?? pendingRows[0]);
        void translateEvents(rows).then((translatedRows) => {
          if (!active) return;
          setEvents(translatedRows);
          setSelected((current) => translatedRows.find((event) => event.id === current?.id) ?? translatedRows[0]);
        });
      })
      .catch(() => {
        if (!active) return;
        const fallback = demoEvent();
        setEvents([fallback]);
        setSelected(fallback);
      });
    return () => {
      active = false;
    };
  }, [queryKey]);

  return { events, selected, setSelected };
}

function prepareEventForChineseDisplay(event: Event): Event {
  if (event.id === "demo") return event;
  if (isChineseText(event.title) && (!event.summary || isChineseText(event.summary))) return event;
  return {
    ...event,
    title_zh: "正在翻译中文标题...",
    summary_zh: "正在翻译中文摘要..."
  };
}

async function translateEvents(events: Event[]): Promise<Event[]> {
  return Promise.all(
    events.map(async (event) => {
      if (event.id === "demo") return event;
      if (isChineseText(event.title) && (!event.summary || isChineseText(event.summary))) return event;
      try {
        const translated = await translateEvent(event.id);
        return { ...event, title_zh: translated.title, summary_zh: translated.summary };
      } catch {
        return {
          ...event,
          title_zh: "中文翻译暂时不可用",
          summary_zh: "这条事件还没有可用中文翻译。请点击“显示原文”查看原始标题和摘要。",
          translation_error: "translation_failed"
        };
      }
    })
  );
}

function isChineseText(value: string): boolean {
  return /[\u4e00-\u9fff]/.test(value);
}

function demoEvent(): Event {
  return {
    id: "demo",
    title: "边境事件出现相互矛盾的伤亡报道",
    title_en: "Cross-border incident draws conflicting casualty reports",
    summary: "多家媒体报道同一事件，但伤亡数字和责任归属存在分歧。",
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
