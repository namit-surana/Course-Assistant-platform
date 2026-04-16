"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  GitBranch,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { mapRunToPlan } from "@/lib/run-utils";
import { ResultsPanel } from "@/components/analyze/results-panel";
import AgentPlan from "@/components/ui/agent-plan";
import type { Submission } from "@/lib/types";

function shortUrl(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
}

interface Props {
  submission: Submission;
  onClose: () => void;
}

export function SubmissionDetailPanel({ submission, onClose }: Props) {
  const run = submission.run;
  const planTasks = mapRunToPlan(run);

  const totalPhases = run.phases.length;
  const donePhases  = run.phases.filter((p) => p.status === "completed").length;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Panel header */}
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-neutral-800 px-4 py-4">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-white truncate">
              {submission.teamName}
            </p>
            <StatusPill status={run.status} />
          </div>
          <a
            href={submission.repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-neutral-400 hover:text-violet-400 transition-colors"
          >
            <GitBranch className="h-3 w-3 shrink-0" />
            <span className="truncate">{shortUrl(submission.repoUrl)}</span>
            <ExternalLink className="h-3 w-3 shrink-0 text-neutral-600" />
          </a>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 rounded-lg p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-white transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">

          {/* Queued */}
          {run.status === "queued" && (
            <motion.div
              key="queued"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6"
            >
              <Clock className="h-8 w-8 text-neutral-500" />
              <p className="text-sm font-medium text-neutral-300">Queued for analysis</p>
              <p className="text-xs text-neutral-600">
                The run will start shortly. This panel will update automatically.
              </p>
            </motion.div>
          )}

          {/* Running */}
          {run.status === "running" && (
            <motion.div
              key="running"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-3 p-4"
            >
              {/* Current activity bar */}
              <div className="rounded-lg border border-violet-500/20 bg-violet-500/8 px-3 py-2.5 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-medium text-violet-300">
                  <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                  <span className="truncate">
                    {run.current_activity ?? "Analyzing…"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full bg-neutral-800 overflow-hidden">
                    <motion.div
                      className="h-full bg-violet-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{
                        width: totalPhases > 0
                          ? `${(donePhases / totalPhases) * 100}%`
                          : "0%",
                      }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-[11px] text-neutral-500 shrink-0">
                    {donePhases}/{totalPhases}
                  </span>
                </div>
              </div>

              {/* Agent plan */}
              <AgentPlan tasks={planTasks} />
            </motion.div>
          )}

          {/* Completed */}
          {run.status === "completed" && (
            <motion.div
              key="completed"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 space-y-4"
            >
              <ResultsPanel
                analysis={run.result?.repository_analysis}
                planTasks={planTasks}
                hideHeader
              />
            </motion.div>
          )}

          {/* Failed */}
          {run.status === "failed" && (
            <motion.div
              key="failed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="m-4 rounded-lg border border-red-500/20 bg-red-500/8 p-4 space-y-2"
            >
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                <p className="text-sm font-semibold text-red-300">Analysis failed</p>
              </div>
              <p className="text-xs text-red-400/80 leading-relaxed">
                {run.error ?? "The analysis could not complete. Check the repository URL and try again."}
              </p>
              {planTasks.length > 0 && (
                <div className="pt-2">
                  <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                    Progress at failure
                  </p>
                  <AgentPlan tasks={planTasks} />
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    queued:    { label: "Queued",    className: "bg-neutral-800 text-neutral-400" },
    running:   { label: "Analyzing", className: "bg-violet-500/15 text-violet-300" },
    completed: { label: "Complete",  className: "bg-emerald-500/15 text-emerald-300" },
    failed:    { label: "Failed",    className: "bg-red-500/15 text-red-300" },
  };
  const c = config[status] ?? config.queued;
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium shrink-0", c.className)}>
      {c.label}
    </span>
  );
}
