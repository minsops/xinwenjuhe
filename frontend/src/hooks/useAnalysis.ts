import { useEffect, useState } from "react";
import { fetchAnalysis } from "../services/api";
import type { EventAnalysis } from "../types/analysis";

export function useAnalysis(eventId?: string, refreshKey = 0) {
  const [analysis, setAnalysis] = useState<EventAnalysis | undefined>();

  useEffect(() => {
    if (!eventId) return;
    if (eventId === "demo") {
      setAnalysis(demoAnalysis());
      return;
    }
    fetchAnalysis(eventId).then(setAnalysis).catch(() => setAnalysis(demoAnalysis()));
  }, [eventId, refreshKey]);

  return analysis;
}

function demoAnalysis(): EventAnalysis {
  return {
    event_id: "demo",
    summary: "多家报道确认夜间发生同一事件，但伤亡数字和责任归属仍存在明显分歧。",
    summary_original: "Multiple reports confirm the same overnight incident, but casualty figures and attribution remain disputed.",
    summary_original_language: "en",
    consensus_facts: [{
      fact: "夜间发生事件，当地应急力量随后介入。",
      fact_original: "An overnight incident occurred and local authorities responded.",
      fact_original_language: "en",
      confirmed_by: 2,
      total: 2,
      article_ids: ["a1"],
      syndicated_count: 1
    }],
    disputed_facts: [{
      topic: "不同来源对伤亡人数的说法从 12 人到 200 多人不等。",
      topic_original: "Sources report casualty figures ranging from 12 to more than 200.",
      topic_original_language: "en",
      type: "number_discrepancy",
      severity: "critical"
    }],
    blind_spots: [{
      description: "多数报道缺少独立现场核验。",
      description_original: "Most reports lack independent on-site verification.",
      description_original_language: "en",
      mentioned_by: 1,
      total: 2
    }],
    narrative_frames: [
      { source_id: "Reuters", frames: ["security", "official_uncertainty"], angle: "factual_report", tone: "neutral" },
      { source_id: "IRNA", frames: ["attack", "external_responsibility"], angle: "responsibility", tone: "strong attribution" }
    ],
    timeline: [
      {
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(),
        fact: "最早报道描述夜间发生事件。",
        fact_original: "The earliest report described an overnight incident.",
        fact_original_language: "en",
        fragment_type: "what",
        article_id: "a1",
        source_id: "Reuters"
      },
      {
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(),
        fact: "不同来源发布了相互冲突的伤亡数字。",
        fact_original: "Different sources published conflicting casualty figures.",
        fact_original_language: "en",
        fragment_type: "number",
        article_id: "a2",
        source_id: "IRNA"
      }
    ],
    source_graph: {
      nodes: [
        { id: "Reuters", type: "source" },
        { id: "IRNA", type: "source" },
        { id: "casualty-count", type: "contradiction", severity: "critical" }
      ],
      edges: [
        { from: "Reuters", to: "a1", type: "reported", fragment_type: "what" },
        { from: "IRNA", to: "a2", type: "reported", fragment_type: "number" },
        { from: "Reuters", to: "casualty-count", type: "number_discrepancy", severity: "critical" },
        { from: "IRNA", to: "casualty-count", type: "number_discrepancy", severity: "critical" }
      ]
    }
  };
}
