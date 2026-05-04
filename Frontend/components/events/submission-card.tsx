"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import {
  GitBranch,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useEventsStore } from "@/lib/events-store";
import { fetchWorkerSubmission, mapWorkerSubmissionToRun } from "@/lib/backend-submissions";
import type { Submission, AnalysisRunState } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

function shortUrl(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
}

interface Props {
  submission: Submission;
  eventId: string;
  isSelected?: boolean;
  onClick?: () => void;
}

export function SubmissionCard({ submission, eventId, isSelected = false, onClick }: Props) {
  const updateSubmission = useEventsStore((s) => s.updateSubmission);
  const sourceRef = useRef<EventSource | null>(null);
  const run = submission.run;
  const voiceStatus = submission.voiceStatus ?? "idle";
  const videoStatus = submission.videoAnalysisStatus ?? "idle";

  useEffect(() => {
    if (run.status !== "queued" && run.status !== "running") return;

    if (submission.workerSubmissionId) {
      let active = true;
      async function refreshWorkerSubmission() {
        if (!submission.workerSubmissionId) return;
        try {
          const detail = await fetchWorkerSubmission(submission.workerSubmissionId);
          if (!active) return;
          updateSubmission(eventId, submission.runId, mapWorkerSubmissionToRun(detail, run));
        } catch {}
      }

      void refreshWorkerSubmission();
      const intervalId = window.setInterval(refreshWorkerSubmission, 5000);
      return () => {
        active = false;
        window.clearInterval(intervalId);
      };
    }

    const source = new EventSource(`${API_BASE_URL}/api/runs/${submission.runId}/stream`);
    sourceRef.current = source;

    source.addEventListener("run", (e) => {
      const payload = JSON.parse(e.data) as AnalysisRunState;
      updateSubmission(eventId, submission.runId, payload);
      if (payload.status === "completed" || payload.status === "failed") {
        source.close();
      }
    });

    source.onerror = async () => {
      source.close();
      try {
        const resp = await fetch(`${API_BASE_URL}/api/runs/${submission.runId}`);
        if (resp.ok) {
          const payload = (await resp.json()) as AnalysisRunState;
          updateSubmission(eventId, submission.runId, payload);
        }
      } catch {}
    };

    return () => source.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventId, run.status, submission.runId, submission.workerSubmissionId, updateSubmission]);

  const totalPhases = run.phases.length;
  const donePhases  = run.phases.filter((p) => p.status === "completed").length;
  const progressPct = totalPhases > 0 ? (donePhases / totalPhases) * 100 : 0;
  const isRunning   = run.status === "running" || run.status === "queued";

  return (
    <motion.button
      layout
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-xl border transition-all duration-200 overflow-hidden",
        "hover:border-neutral-700",
        isSelected
          ? "border-violet-500/50 bg-neutral-900 shadow-[inset_3px_0_0_0] shadow-violet-500"
          : "border-neutral-800 bg-neutral-900/60 hover:bg-neutral-900",
      )}
    >
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3.5">
        {/* Left: names */}
        <div className="flex-1 min-w-0">
          <p className={cn(
            "text-sm font-semibold truncate leading-tight",
            isSelected ? "text-white" : "text-neutral-200",
          )}>
            {submission.teamName}
          </p>
          <div className="flex items-center gap-1 mt-0.5">
            <GitBranch className="h-3 w-3 text-neutral-600 shrink-0" />
            <span className="text-xs text-neutral-500 truncate">
              {shortUrl(submission.repoUrl)}
            </span>
          </div>
        </div>

        {/* Right: status + chevron */}
        <div className="flex items-center gap-2 shrink-0">
          <StatusPill status={run.status} />
          <ChevronRight className={cn(
            "h-4 w-4 transition-all duration-200",
            isSelected ? "text-violet-400 rotate-90" : "text-neutral-600",
          )} />
        </div>
      </div>

      {/* Progress bar — only while running */}
      {isRunning && (
        <div className="px-4 pb-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-neutral-500">
            <span className="flex items-center gap-1.5 truncate">
              <Loader2 className="h-2.5 w-2.5 animate-spin text-violet-400 shrink-0" />
              <span className="truncate">
                {run.current_activity ?? (run.status === "queued" ? "Queued…" : "Analyzing…")}
              </span>
            </span>
            <span className="shrink-0 ml-2 tabular-nums">
              {donePhases}/{totalPhases}
            </span>
          </div>
          <div className="h-0.5 w-full rounded-full bg-neutral-800 overflow-hidden">
            <motion.div
              className="h-full bg-violet-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
          </div>
        </div>
      )}

      {/* Failed hint */}
      {run.status === "failed" && (
        <p className="px-4 pb-3 text-[11px] text-red-500 truncate">
          {run.error ?? "Analysis failed — click for details"}
        </p>
      )}

      <p className="px-4 pb-3 text-[11px] text-neutral-500">
        Voice: {voiceStatus} • Video: {videoStatus}
      </p>
    </motion.button>
  );
}

function StatusPill({ status }: { status: AnalysisRunState["status"] }) {
  if (status === "queued") return (
    <span className="flex items-center gap-1 rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] font-medium text-neutral-400">
      <Clock className="h-2.5 w-2.5" /> Queued
    </span>
  );
  if (status === "running") return (
    <span className="flex items-center gap-1 rounded-full bg-violet-500/15 px-2 py-0.5 text-[11px] font-medium text-violet-300">
      <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-pulse" />
      Analyzing
    </span>
  );
  if (status === "completed") return (
    <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
      <CheckCircle2 className="h-2.5 w-2.5" /> Complete
    </span>
  );
  return (
    <span className="flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-medium text-red-300">
      <XCircle className="h-2.5 w-2.5" /> Failed
    </span>
  );
}
