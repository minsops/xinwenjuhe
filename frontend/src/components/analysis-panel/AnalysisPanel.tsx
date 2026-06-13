import { RefreshCw } from "lucide-react";
import { useState } from "react";
import type { EventAnalysis } from "../../types/analysis";
import { startEventPipeline } from "../../services/api";
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
  sourceLabels?: Record<string, string>;
  onFactSelect?: (articleId: string, fact: string) => void;
  onReanalyze?: () => void;
};

export function AnalysisPanel({ analysis, eventId, sourceLabels = {}, onFactSelect, onReanalyze }: Props) {
  const [running, setRunning] = useState(false);
  const [reanalyzeNotice, setReanalyzeNotice] = useState<string | undefined>();
  const analyzedReportCount = analysis.article_count_at_analysis ?? analysis.consensus_facts[0]?.total ?? 0;

  async function handleReanalyze() {
    if (!eventId || running) return;
    setRunning(true);
    setReanalyzeNotice(undefined);
    try {
      await startEventPipeline(eventId);
      setReanalyzeNotice("已加入后台分析队列，完成后页面会自动更新。");
      onReanalyze?.();
    } catch {
      setReanalyzeNotice("重新分析提交失败，请检查后端任务服务。");
    } finally {
      setRunning(false);
    }
  }

  return (
    <aside className="soft-scrollbar h-full overflow-y-auto bg-stone-50/80 dark:bg-stone-950">
      <div className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 px-5 py-4 shadow-sm backdrop-blur dark:border-stone-800 dark:bg-stone-950/95">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-civic dark:text-cyan-200">本站分析</div>
            <div className="mt-1 text-sm text-stone-500 dark:text-stone-400">v{analysis.analysis_version ?? 1} · {analysis.article_count_at_analysis ?? "?"} 篇报道</div>
          </div>
          <button
            className="focus-ring inline-flex items-center justify-center gap-2 rounded-2xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300 hover:shadow disabled:translate-y-0 disabled:opacity-60 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-100"
            onClick={handleReanalyze}
            disabled={running || !eventId}
          >
            <RefreshCw className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />
            {running ? "提交中..." : "重新分析"}
          </button>
        </div>
        {reanalyzeNotice ? <div className="mt-3 text-xs text-stone-500 dark:text-stone-400">{reanalyzeNotice}</div> : null}
      </div>
      <div className="m-4 rounded-2xl border border-cyan-100 bg-cyan-50/90 px-4 py-3 text-sm leading-6 text-cyan-950 dark:border-cyan-900 dark:bg-cyan-950/50 dark:text-cyan-100">
        本站把多家媒体报道拆成事实、争议和盲区。下面不是外站搬运，而是本站对同一事件的结构化分析。
      </div>
      <div className="space-y-3 px-4 pb-4">
        <EventSummary
          summary={analysis.summary}
          summaryOriginal={analysis.summary_original}
          summaryOriginalLanguage={analysis.summary_original_language}
          count={analyzedReportCount}
        />
        <ConsensusZone items={analysis.consensus_facts} onFactSelect={onFactSelect} />
        <DisputeZone items={analysis.disputed_facts} />
        <BlindSpotZone items={analysis.blind_spots} />
        <EventTimeline items={analysis.timeline} />
        <SourceGraph graph={analysis.source_graph} sourceLabels={sourceLabels} />
        <NarrativeFrameComparison frames={analysis.narrative_frames} sourceLabels={sourceLabels} />
      </div>
    </aside>
  );
}
