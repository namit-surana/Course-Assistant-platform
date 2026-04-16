"use client";

import type { AnalysisRunState } from "@/lib/types";

interface RecentRunsPanelProps {
  runs: AnalysisRunState[];
  activeRunId?: string | null;
  onOpenRun: (runId: string) => void;
}

export function RecentRunsPanel({
  runs,
  activeRunId,
  onOpenRun,
}: RecentRunsPanelProps) {
  if (!runs.length) {
    return (
      <section className="rounded-[1.5rem] border border-border/70 bg-card/60 p-5">
        <p className="text-sm text-muted-foreground">No recent evaluations yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[1.5rem] border border-border/70 bg-card/60 p-5">
      <div className="mb-4 space-y-1">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
          Recent Runs
        </p>
        <h2 className="text-lg font-semibold tracking-[-0.03em]">Open a previous evaluation</h2>
      </div>

      <div className="space-y-2">
        {runs.map((run) => {
          const label =
            run.owner && run.repo ? `${run.owner}/${run.repo}` : run.request.repo_url;
          const isActive = activeRunId === run.id;
          return (
            <button
              key={run.id}
              type="button"
              onClick={() => onOpenRun(run.id)}
              className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition ${
                isActive
                  ? "border-blue-500/30 bg-blue-500/8"
                  : "border-border/70 bg-background/40 hover:bg-background/70"
              }`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{label}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {run.branch ? `Branch: ${run.branch}` : "Branch pending"} · {run.status}
                </p>
              </div>
              <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-medium text-secondary-foreground">
                {run.status}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
