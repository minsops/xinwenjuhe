import { RefreshCw } from "lucide-react";
import { useState } from "react";
import type { EventAnalysis } from "../../types/analysis";
import { runEventAnalysis } from "../../services/api";
import { BlindSpotZone } from "./BlindSpotZone";
import { ConsensusZone } from "./ConsensusZone";
import { DisputeZone } from "./DisputeZone";
import { EventTimeline } from "./EventTimeline";
import { EventSummary } from "./EventSummary";
import { NarrativeFrameComparison } from "./NarrativeFrameComparison";
import { SourceGraph } from "./SourceGraph";

type Props = {
  analysis: EventAnalysis;
  eventId?: string;
  onFactSelect?: (articleId: string, fact: string) => void;
  onReanalyze?: () => void;
};

export function AnalysisPanel({ analysis, eventId, onFactSelect, onReanalyze }: Props) {
  const [running, setRunning] = useState(false);

  async function handleReanalyze() {
    if (!eventId || running) return;
    setRunning(true);
    try {
      await runEventAnalysis(eventId);
      onReanalyze?.();
    } catch {
      return;
    } finally {
      setRunning(false);
    }
  }

  return (
    <aside className="h-full overflow-y-auto bg-stone-50 dark:bg-stone-900">
      <div className="flex items-center justify-between border-b border-stone-300 px-4 py-2 dark:border-stone-700">
        <span className="text-xs text-stone-500">
          v{analysis.analysis_version ?? 1} · {analysis.article_count_at_analysis ?? "?"} articles
        </span>
        <button
          className="focus-ring inline-flex items-center gap-1 rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-60 dark:border-stone-700"
          onClick={handleReanalyze}
          disabled={running || !eventId}
        >
          <RefreshCw className={`h-3 w-3 ${running ? "animate-spin" : ""}`} />
          {running ? "Analyzing..." : "Re-analyze"}
        </button>
      </div>
      <EventSummary summary={analysis.summary} count={analysis.consensus_facts[0]?.total ?? 0} />
      <ConsensusZone items={analysis.consensus_facts} onFactSelect={onFactSelect} />
      <DisputeZone items={analysis.disputed_facts} />
      <BlindSpotZone items={analysis.blind_spots} />
      <EventTimeline items={analysis.timeline} />
      <SourceGraph graph={analysis.source_graph} />
      <NarrativeFrameComparison frames={analysis.narrative_frames} />
    </aside>
  );
}
