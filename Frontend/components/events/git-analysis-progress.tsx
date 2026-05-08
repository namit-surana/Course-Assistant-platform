"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, ChevronRight, CircleDashed, Loader2, X } from "lucide-react";

import { fetchRunState } from "@/lib/backend-submissions";
import type { AnalysisRunState, ItemStatus, RunPhaseState } from "@/lib/types";
import { cn } from "@/lib/utils";

type Props = {
  runId: string;
  onCompleted?: () => void;
  collapsible?: boolean;
  defaultOpen?: boolean;
  collapseOnComplete?: boolean;
};

export function GitAnalysisProgress({
  runId,
  onCompleted,
  collapsible = false,
  defaultOpen = true,
  collapseOnComplete = false,
}: Props) {
  const [state, setState] = useState<AnalysisRunState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(defaultOpen);
  const completedRef = useRef(false);
  const autoCollapsedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: number | null = null;

    async function tick() {
      try {
        const next = await fetchRunState(runId);
        if (cancelled) return;
        setState(next);
        setError(null);

        if (
          (next.status === "completed" || next.status === "failed") &&
          !completedRef.current
        ) {
          completedRef.current = true;
          onCompleted?.();
          if (collapseOnComplete && !autoCollapsedRef.current) {
            autoCollapsedRef.current = true;
            setOpen(false);
          }
        }

        if (next.status === "completed" || next.status === "failed") {
          if (timer !== null) {
            window.clearInterval(timer);
            timer = null;
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unable to load run state.");
        }
      }
    }

    void tick();
    timer = window.setInterval(() => void tick(), 1000);

    return () => {
      cancelled = true;
      if (timer !== null) window.clearInterval(timer);
    };
  }, [runId, onCompleted]);

  if (!state && !error) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-neutral-800 bg-neutral-950/40 p-4 text-sm text-neutral-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading analysis progress…
      </div>
    );
  }

  if (error && !state) {
    return (
      <div className="rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-200">
        {error}
      </div>
    );
  }

  if (!state) return null;

  const kind = (state as { kind?: "repo" | "ppt" | "video" | "final" }).kind ?? "repo";
  const titleByKind: Record<typeof kind, string> = {
    repo: "Repository analysis",
    ppt: "Presentation analysis",
    video: "Demo video analysis",
    final: "Final grading",
  };
  const title = titleByKind[kind];

  let detailLine = "";
  if (kind === "repo") {
    detailLine =
      state.owner && state.repo
        ? `${state.owner}/${state.repo}${state.branch ? `@${state.branch}` : ""}`
        : "Resolving repository…";
  } else {
    detailLine = (state as { label?: string | null }).label ?? "";
  }

  const completedSubtaskCount = state.phases.reduce(
    (acc, p) =>
      acc +
      p.subtasks.filter((s) => s.status === "completed" || s.status === "skipped").length,
    0,
  );
  const totalSubtaskCount = state.phases.reduce((acc, p) => acc + p.subtasks.length, 0);
  const progressLabel = totalSubtaskCount
    ? `${completedSubtaskCount}/${totalSubtaskCount} steps`
    : null;

  const HeaderTag = collapsible ? "button" : "div";

  return (
    <div className="space-y-4 rounded-lg border border-neutral-800 bg-neutral-950/40 p-4">
      <HeaderTag
        type={collapsible ? "button" : undefined}
        onClick={collapsible ? () => setOpen((prev) => !prev) : undefined}
        className={cn(
          "flex w-full items-center justify-between gap-3 text-left",
          collapsible && "cursor-pointer rounded-md hover:bg-neutral-900/40 -mx-2 px-2 py-1",
        )}
      >
        <div className="flex min-w-0 items-center gap-2">
          {collapsible ? (
            open ? (
              <ChevronDown className="h-4 w-4 flex-shrink-0 text-neutral-500" />
            ) : (
              <ChevronRight className="h-4 w-4 flex-shrink-0 text-neutral-500" />
            )
          ) : null}
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-neutral-200">{title}</div>
            {detailLine ? (
              <div className="truncate text-xs text-neutral-500">{detailLine}</div>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {progressLabel && !open ? (
            <span className="text-[11px] text-neutral-500">{progressLabel}</span>
          ) : null}
          <RunStatusPill status={state.status} />
        </div>
      </HeaderTag>

      {open ? (
        <>
          {state.current_activity ? (
            <div className="rounded-md bg-neutral-900/60 px-3 py-2 text-xs text-neutral-300">
              <span className="text-neutral-500">Activity: </span>
              {state.current_activity}
            </div>
          ) : null}

          <div className="space-y-3">
            {state.phases.map((phase) => (
              <PhaseRow key={phase.id} phase={phase} />
            ))}
          </div>

          {state.error ? (
            <div className="rounded-md border border-red-900/50 bg-red-950/30 px-3 py-2 text-xs text-red-200">
              {state.error}
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function PhaseRow({ phase }: { phase: RunPhaseState }) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm">
        <StatusIcon status={phase.status} />
        <span className="font-medium text-neutral-100">{phase.title}</span>
      </div>
      <ul className="ml-6 mt-1 space-y-1 text-xs text-neutral-300">
        {phase.subtasks.map((subtask) => (
          <li key={subtask.id} className="flex items-start gap-2">
            <span className="mt-0.5">
              <StatusIcon status={subtask.status} small />
            </span>
            <div className="flex-1">
              <div>
                <span
                  className={cn(
                    subtask.status === "completed" && "text-neutral-400",
                    subtask.status === "in-progress" && "text-neutral-100",
                  )}
                >
                  {subtask.title}
                </span>
                {subtask.detail ? (
                  <span className="text-neutral-500"> — {subtask.detail}</span>
                ) : null}
              </div>
              {subtask.activity_log.length > 0 && subtask.status === "in-progress" ? (
                <ul className="mt-0.5 space-y-0.5 text-[11px] text-neutral-500">
                  {subtask.activity_log.slice(-2).map((line, idx) => (
                    <li key={idx}>» {line}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatusIcon({ status, small = false }: { status: ItemStatus; small?: boolean }) {
  const size = small ? "h-3 w-3" : "h-4 w-4";

  if (status === "completed") {
    return <Check className={cn(size, "text-emerald-400")} />;
  }
  if (status === "in-progress") {
    return <Loader2 className={cn(size, "animate-spin text-violet-300")} />;
  }
  if (status === "failed") {
    return <X className={cn(size, "text-red-400")} />;
  }
  if (status === "skipped") {
    return <CircleDashed className={cn(size, "text-neutral-600")} />;
  }
  return <CircleDashed className={cn(size, "text-neutral-700")} />;
}

function RunStatusPill({ status }: { status: AnalysisRunState["status"] }) {
  const base =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold";

  if (status === "running")
    return <span className={cn(base, "bg-violet-500/15 text-violet-200")}>Running</span>;
  if (status === "completed")
    return <span className={cn(base, "bg-emerald-500/15 text-emerald-200")}>Completed</span>;
  if (status === "failed")
    return <span className={cn(base, "bg-red-500/15 text-red-200")}>Failed</span>;
  return <span className={cn(base, "bg-neutral-800 text-neutral-300")}>Queued</span>;
}
