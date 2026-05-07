import { ArrowUpRight, CheckCircle2, Clock3, Loader2, AlertCircle, Play, Eye, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ComponentType, SVGProps } from "react";
import { useState } from "react";

type SubmissionStatus = "submitted" | "processing" | "completed" | "failed";

const statusMeta: Record<SubmissionStatus, {
  label: string;
  badge: string;
  progressColor: string;
  helper: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}> = {
  submitted: {
    label: "Submitted",
    badge: "text-slate-900 bg-slate-200/90 ring-slate-300/60",
    progressColor: "bg-slate-400",
    helper: "Submission received and awaiting processing.",
    icon: Clock3,
  },
  processing: {
    label: "Processing",
    badge: "text-sky-200 bg-sky-500/15 ring-sky-400/20",
    progressColor: "bg-sky-400",
    helper: "Your submission is actively being analyzed.",
    icon: Loader2,
  },
  completed: {
    label: "Completed",
    badge: "text-emerald-200 bg-emerald-500/15 ring-emerald-400/20",
    progressColor: "bg-emerald-400",
    helper: "Analysis complete and the report is ready.",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    badge: "text-rose-200 bg-rose-500/15 ring-rose-400/20",
    progressColor: "bg-rose-400",
    helper: "An issue occurred during processing.",
    icon: AlertCircle,
  },
};

export interface SubmissionStatusCardProps {
  title: string;
  team: string;
  status: SubmissionStatus;
  progress: number;
  timeLabel: string;
  summary: string;
  details: Array<{ label: string; value: string }>;
}

export function SubmissionStatusCard({
  title,
  team,
  status,
  progress,
  timeLabel,
  summary,
  details,
}: SubmissionStatusCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const meta = statusMeta[status];
  const StatusIcon = meta.icon;
  const progressWidth = `${Math.min(Math.max(progress, 0), 100)}%`;

  return (
    <Card className="h-full rounded-[2rem] border border-slate-800/80 bg-gradient-to-br from-slate-950/95 via-slate-900/95 to-slate-950/95 shadow-2xl shadow-slate-950/20 transition duration-300 hover:-translate-y-1 hover:shadow-[0_30px_80px_-36px_rgba(15,23,42,0.55)]">
      <CardHeader className="grid gap-5 px-6 pb-5 pt-6 sm:grid-cols-[1fr_auto] sm:items-start">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] ring-1",
                meta.badge,
              )}
            >
              <StatusIcon className={cn("h-3.5 w-3.5", status === "processing" ? "animate-spin" : "")} />
              {meta.label}
            </span>

            <span className="rounded-full bg-slate-900/80 px-3 py-1 text-xs font-medium text-slate-400">
              {timeLabel}
            </span>
          </div>

          <div className="space-y-3">
            <CardTitle className="text-2xl font-semibold leading-tight text-white sm:text-3xl">{title}</CardTitle>
            <CardDescription className="max-w-xl text-sm leading-6 text-slate-400 sm:text-base">
              {summary}
            </CardDescription>
          </div>
        </div>

        <div className="rounded-[1.75rem] border border-slate-800/80 bg-slate-900/75 p-4 text-right shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Team</p>
          <p className="mt-2 text-xl font-semibold text-white">{team}</p>
        </div>
      </CardHeader>

      <CardContent className="grid gap-6 px-6 pb-6 sm:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-6">
          <div className="space-y-4 rounded-3xl border border-slate-800/80 bg-slate-900/75 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-400">Overall progress</p>
                <p className="mt-1 text-3xl font-semibold text-white">{Math.round(progress)}%</p>
              </div>
              <span className={cn(
                "rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em]",
                meta.badge,
              )}
              >
                {meta.label}
              </span>
            </div>

            <div className="space-y-3">
              <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={cn("h-full rounded-full transition-all duration-500", meta.progressColor)}
                  style={{ width: progressWidth }}
                />
              </div>
              <p className="text-sm text-slate-500">{meta.helper}</p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {details.map((detail) => (
              <div key={detail.label} className="rounded-3xl bg-slate-900/75 p-4 ring-1 ring-slate-800/70">
                <p className="text-sm font-medium text-slate-400">{detail.label}</p>
                <p className="mt-2 text-base font-semibold text-white">{detail.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-3xl bg-slate-900/75 p-5 ring-1 ring-slate-800/80">
          <div className="flex items-center justify-between text-sm text-slate-400">
            <p className="font-medium">Status details</p>
            <ArrowUpRight className="h-4 w-4 text-slate-400" />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-300">{summary}</p>

          <div className="mt-6 space-y-3">
            <div className="flex items-center justify-between rounded-3xl bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <span>File validation</span>
              <span className="text-slate-100">Complete</span>
            </div>
            <div className="flex items-center justify-between rounded-3xl bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <span>Review readiness</span>
              <span className="text-slate-100">Queued</span>
            </div>
          </div>
        </div>
      </CardContent>

      {status === "submitted" && (
        <div className="px-6 pb-6">
          <Button
            onClick={() => setIsLoading(true)}
            disabled={isLoading}
            className={cn(
              "w-full rounded-2xl font-semibold py-3 text-white transition-all duration-200",
              "bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-700 hover:to-blue-600",
              "hover:shadow-lg hover:shadow-blue-500/25 hover:scale-[1.02]",
              "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100",
              "focus:ring-2 focus:ring-blue-500/50 focus:outline-none"
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting Analysis...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Start Analysis
              </>
            )}
          </Button>
        </div>
      )}

      {status === "completed" && (
        <div className="px-6 pb-6">
          <Button
            className={cn(
              "w-full rounded-2xl font-semibold py-3 text-white transition-all duration-200",
              "bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600",
              "hover:shadow-lg hover:shadow-emerald-500/25 hover:scale-[1.02]",
              "focus:ring-2 focus:ring-emerald-500/50 focus:outline-none"
            )}
          >
            <Eye className="mr-2 h-4 w-4" />
            View Report
          </Button>
        </div>
      )}

      {status === "failed" && (
        <div className="px-6 pb-6">
          <Button
            className={cn(
              "w-full rounded-2xl font-semibold py-3 text-white transition-all duration-200",
              "bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-700 hover:to-rose-600",
              "hover:shadow-lg hover:shadow-rose-500/25 hover:scale-[1.02]",
              "focus:ring-2 focus:ring-rose-500/50 focus:outline-none"
            )}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Retry Analysis
          </Button>
        </div>
      )}
    </Card>
  );
}
