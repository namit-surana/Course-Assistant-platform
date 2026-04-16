"use client";

import type { AnalysisRunState } from "@/lib/types";

export function RunHeader({
  run,
  title,
  footer,
}: {
  run: AnalysisRunState;
  title: string;
  footer?: React.ReactNode;
}) {
  return (
    <section className="rounded-[1.5rem] border border-border/70 bg-card/70 px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1.5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
            {title}
          </p>
          <h1 className="text-[1.75rem] font-semibold tracking-[-0.05em]">
            {run.owner && run.repo ? `${run.owner}/${run.repo}` : "Repository run"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {run.current_activity || "Waiting for the next state update."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span className="rounded-full bg-blue-500/10 px-3 py-1 font-medium text-blue-400">
            {run.status}
          </span>
          {run.branch ? <span>Branch: {run.branch}</span> : null}
        </div>
      </div>
      {footer ? <div className="mt-4 border-t border-border/70 pt-3">{footer}</div> : null}
    </section>
  );
}
