import { useEffect, useState } from "react";
import { fetchAnalysis } from "../services/api";
import type { EventAnalysis } from "../types/analysis";

export function useAnalysis(eventId?: string, refreshKey = 0) {
  const [analysis, setAnalysis] = useState<EventAnalysis | undefined>();

  useEffect(() => {
    let active = true;
    if (!eventId) {
      setAnalysis(undefined);
      return () => {
        active = false;
      };
    }
    setAnalysis(undefined);
    if (eventId === "demo") {
      setAnalysis(demoAnalysis());
      return () => {
        active = false;
      };
    }
    fetchAnalysis(eventId)
      .then((nextAnalysis) => {
        if (active) setAnalysis(nextAnalysis);
      })
      .catch(() => {
        if (active) setAnalysis(demoAnalysis());
      });
    return () => {
      active = false;
    };
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
      {
        source_id: "Reuters",
        frames: ["安全事件", "官方不确定性"],
        frames_original: ["security", "official_uncertainty"],
        frames_original_language: "en",
        angle: "事实报道",
        angle_original: "factual_report",
        angle_original_language: "en",
        emphasis: ["官方仍在核实原因"],
        emphasis_original: ["official uncertainty"],
        emphasis_original_language: "en",
        downplayed: ["责任归属"],
        downplayed_original: ["attribution"],
        downplayed_original_language: "en",
        tone: "中性",
        tone_original: "neutral",
        tone_original_language: "en",
        wording: ["据官员称", "仍在调查"],
        wording_original: ["officials said", "under investigation"],
        wording_original_language: "en"
      },
      {
        source_id: "IRNA",
        frames: ["袭击叙事", "外部责任"],
        frames_original: ["attack", "external_responsibility"],
        frames_original_language: "en",
        angle: "责任归属",
        angle_original: "responsibility",
        angle_original_language: "en",
        emphasis: ["更高的受影响人数"],
        emphasis_original: ["higher affected count"],
        emphasis_original_language: "en",
        downplayed: ["独立核验状态"],
        downplayed_original: ["independent verification status"],
        downplayed_original_language: "en",
        tone: "强烈归责",
        tone_original: "strong attribution",
        tone_original_language: "en",
        wording: ["外国势力"],
        wording_original: ["foreign forces"],
        wording_original_language: "en"
      }
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
