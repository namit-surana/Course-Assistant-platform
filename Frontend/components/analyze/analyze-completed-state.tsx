"use client";

import { useState } from "react";
import { List } from "lucide-react";

import { RecentRunsPanel } from "@/components/analyze/recent-runs-panel";
import { ResultsPanel } from "@/components/analyze/results-panel";
import { RunHeader } from "@/components/analyze/run-header";
import { Button } from "@/components/ui/button";
import type { AnalysisRunState, PlanTask } from "@/lib/types";

export function AnalyzeCompletedState({
  run,
  planTasks,
  recentRuns,
  onOpenRun,
  onStartNewAnalysis,
}: {
  run: AnalysisRunState;
  planTasks: PlanTask[];
  recentRuns: AnalysisRunState[];
  onOpenRun: (runId: string) => void;
  onStartNewAnalysis: () => void;
}) {
  const [showRecentRuns, setShowRecentRuns] = useState(false);
  const analysis = run.result?.repository_analysis;
  const evidenceCount = analysis?.evidence_paths?.length ?? 0;

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-8 xl:max-w-6xl 2xl:max-w-7xl">
        <RunHeader
          run={run}
          title="Evaluation Result"
          footer={
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <span>{evidenceCount} evidence path{evidenceCount === 1 ? "" : "s"} surfaced</span>
                <span className="hidden sm:inline text-border">/</span>
                <span>Findings are primary in this view</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="rounded-full px-4"
                  onClick={() => setShowRecentRuns((current) => !current)}
                >
                  <List className="size-4" />
                  {showRecentRuns ? "Hide Recent Runs" : "Recent Runs"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="rounded-full px-4"
                  onClick={onStartNewAnalysis}
                >
                  Start New Analysis
                </Button>
              </div>
            </div>
          }
        />

        <ResultsPanel
          analysis={analysis}
          planTasks={planTasks}
        />

        {showRecentRuns ? (
          <section className="space-y-3">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-[-0.03em]">Recent evaluations</h2>
              <p className="text-sm text-muted-foreground">
                Reopen a previous run without pulling attention away from the active findings view.
              </p>
            </div>
            <RecentRunsPanel runs={recentRuns} activeRunId={run.id} onOpenRun={onOpenRun} />
          </section>
        ) : null}
      </div>
    </main>
  );
}
