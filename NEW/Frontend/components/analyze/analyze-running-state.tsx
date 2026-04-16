"use client";

import AgentPlan from "@/components/ui/agent-plan";
import { Button } from "@/components/ui/button";
import type { AnalysisRunState, PlanTask } from "@/lib/types";

import { RecentRunsPanel } from "@/components/analyze/recent-runs-panel";
import { RunHeader } from "@/components/analyze/run-header";

export function AnalyzeRunningState({
  run,
  planTasks,
  failedStep,
  recentRuns,
  onOpenRun,
  onStartNewAnalysis,
}: {
  run: AnalysisRunState;
  planTasks: PlanTask[];
  failedStep: { phaseTitle: string; subtaskTitle: string; detail?: string | null } | null;
  recentRuns: AnalysisRunState[];
  onOpenRun: (runId: string) => void;
  onStartNewAnalysis: () => void;
}) {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <RunHeader run={run} title="Live Evaluation" />

        <div className="flex justify-end">
          <Button type="button" variant="secondary" className="rounded-full px-4" onClick={onStartNewAnalysis}>
            Start New Analysis
          </Button>
        </div>

        {run.status === "failed" ? (
          <section className="rounded-[1.75rem] border border-red-400/20 bg-red-500/10 px-5 py-4">
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-red-300">
                Run Failed
              </p>
              <h2 className="text-lg font-semibold text-red-100">
                {run.error || "The repository analysis run could not complete."}
              </h2>
              <p className="text-sm text-red-100/80">
                {failedStep
                  ? `Stopped at ${failedStep.phaseTitle} -> ${failedStep.subtaskTitle}.`
                  : "The backend ended the run before the final report could be generated."}
              </p>
              {failedStep?.detail ? (
                <div className="pt-1">
                  <span className="rounded-full bg-red-500/10 px-3 py-1 text-xs font-medium text-red-100">
                    {failedStep.detail}
                  </span>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section className="space-y-4">
            <div className="space-y-1">
              <h2 className="text-xl font-semibold tracking-[-0.04em]">Execution timeline</h2>
              <p className="text-sm text-muted-foreground">
                Follow the live specialist workflow and keep completed activity attached to each
                phase.
              </p>
            </div>
            <AgentPlan tasks={planTasks} />
          </section>

          <RecentRunsPanel runs={recentRuns} activeRunId={run.id} onOpenRun={onOpenRun} />
        </div>
      </div>
    </main>
  );
}
