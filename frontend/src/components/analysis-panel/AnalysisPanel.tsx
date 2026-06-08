import type { EventAnalysis } from "../../types/analysis";
import { BlindSpotZone } from "./BlindSpotZone";
import { ConsensusZone } from "./ConsensusZone";
import { DisputeZone } from "./DisputeZone";
import { EventTimeline } from "./EventTimeline";
import { EventSummary } from "./EventSummary";
import { NarrativeFrameComparison } from "./NarrativeFrameComparison";
import { SourceGraph } from "./SourceGraph";

type Props = {
  analysis: EventAnalysis;
  onFactSelect?: (articleId: string, fact: string) => void;
};

export function AnalysisPanel({ analysis, onFactSelect }: Props) {
  return (
    <aside className="h-full overflow-y-auto bg-stone-50 dark:bg-stone-900">
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
