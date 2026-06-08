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
    summary: "Available reports agree that an overnight incident occurred, but the casualty count and responsibility claims differ sharply across sources.",
    consensus_facts: [{ fact: "An overnight incident occurred and local authorities responded.", confirmed_by: 2, total: 2, article_ids: ["a1"] }],
    disputed_facts: [{ topic: "Casualty count differs between 12 and more than 200.", type: "number_discrepancy", severity: "critical" }],
    blind_spots: [{ description: "Independent on-site verification is absent from most reports.", mentioned_by: 1, total: 2 }],
    narrative_frames: [
      { source_id: "Reuters", frames: ["security incident", "official uncertainty"], tone: "neutral" },
      { source_id: "IRNA", frames: ["attack", "foreign responsibility"], tone: "hostile" }
    ],
    timeline: [
      { timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8).toISOString(), fact: "Initial local reports described an overnight incident.", fragment_type: "what", article_id: "a1", source_id: "Reuters" },
      { timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4).toISOString(), fact: "Officials released conflicting casualty figures.", fragment_type: "number", article_id: "a2", source_id: "IRNA" }
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
