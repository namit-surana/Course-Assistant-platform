"use client";

import { CheckCircle2, Clock3, Loader2, AlertCircle, Play, Eye, RotateCcw } from "lucide-react";
import { useRouter } from "next/navigation";
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
    badge: "bg-slate-700/60 text-slate-200 border-slate-600/40",
    progressColor: "bg-slate-500",
    helper: "Submission received and awaiting processing.",
    icon: Clock3,
  },
  processing: {
    label: "Processing",
    badge: "bg-blue-900/40 text-blue-200 border-blue-700/40",
    progressColor: "bg-blue-500",
    helper: "Your submission is actively being analyzed.",
    icon: Loader2,
  },
  completed: {
    label: "Completed",
    badge: "bg-emerald-900/40 text-emerald-200 border-emerald-700/40",
    progressColor: "bg-emerald-500",
    helper: "Analysis complete and the report is ready.",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    badge: "bg-rose-900/40 text-rose-200 border-rose-700/40",
    progressColor: "bg-rose-500",
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
  submissionId?: string;
  eventId?: string;
}

export function SubmissionStatusCard({
  title,
  team,
  status,
  progress,
  timeLabel,
  summary,
  details,
  submissionId,
  eventId,
}: SubmissionStatusCardProps) {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const meta = statusMeta[status];
  const StatusIcon = meta.icon;
  const progressWidth = `${Math.min(Math.max(progress, 0), 100)}%`;
  const hasRouteTarget = Boolean(eventId && submissionId);

  const artifactType = details.find((detail) => detail.label === "Artifact type")?.value ?? "—";
  const reviewEta = details.find((detail) => detail.label === "Review ETA")?.value ?? "—";
  const nextStep = details.find((detail) => detail.label === "Next step")?.value ?? "—";

  const handleStartAnalysis = () => {
    setIsLoading(true);
    console.log("Start Analysis clicked — wire this to the real submission processing flow.");
    window.setTimeout(() => setIsLoading(false), 800);
  };

  const handleViewReport = () => {
    if (hasRouteTarget) {
      // Navigate to the submission detail page - it exists but may show "not found" for mock data
      router.push(`/events/${eventId}/submissions/${submissionId}`);
      return;
    }

    // For demo/mock data without real routes, show a simple alert
    alert(`Report for "${title}" - This is a demo. Real reports would show detailed analysis results here.`);
  };

  const handleRetry = () => {
    // Retry should trigger the same analysis logic as Start Analysis
    console.log("Retry clicked for submission:", { submissionId, title, team });
    // TODO: hook retry into the actual submission retry flow when backend route exists
    // For now, simulate the same start analysis flow
    handleStartAnalysis();
  };

  return (
    <tr className="border-t border-slate-600/30 text-left text-[13px] text-slate-200 align-top hover:bg-slate-700/20 transition-colors">
      <td className="px-3 py-4 align-top align-middle">
        <div className="max-w-[220px]">
          <p className="font-semibold text-slate-100 truncate">{title}</p>
          <p className="mt-1 truncate text-[11px] leading-5 text-slate-400">{summary}</p>
          <p className="mt-2 text-[10px] uppercase tracking-[0.24em] text-slate-500">{timeLabel}</p>
        </div>
      </td>
      <td className="px-3 py-4 align-top whitespace-nowrap align-middle">
        <p className="font-medium text-slate-100">{team}</p>
      </td>
      <td className="px-3 py-4 align-top align-middle">
        <div className="flex flex-col gap-1">
          <span className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.22em]",
            meta.badge
          )}>
            <StatusIcon className={cn("h-3 w-3", status === "processing" ? "animate-spin" : "")} />
            {meta.label}
          </span>
          <p className="text-[11px] text-slate-400">{meta.helper}</p>
        </div>
      </td>
      <td className="px-3 py-4 align-top w-[90px] align-middle">
        <div className="font-semibold text-slate-100">{Math.round(progress)}%</div>
        <div className="mt-2 h-2 rounded-full bg-slate-600/40">
          <div
            className={cn("h-full rounded-full transition-all duration-700 ease-out", meta.progressColor)}
            style={{ width: progressWidth }}
          />
        </div>
      </td>
      <td className="px-3 py-4 align-top whitespace-nowrap align-middle">
        <p className="font-medium text-slate-100">{artifactType}</p>
      </td>
      <td className="px-3 py-4 align-top whitespace-nowrap align-middle">
        <p className="font-medium text-slate-100">{reviewEta}</p>
      </td>
      <td className="px-3 py-4 align-top whitespace-nowrap align-middle">
        <p className="font-medium text-slate-100">{nextStep}</p>
      </td>
      <td className="px-3 py-4 align-top w-[132px] align-middle">
        {status === "submitted" && (
          <Button
            type="button"
            onClick={handleStartAnalysis}
            disabled={isLoading}
            className={cn(
              "w-full rounded-lg px-3 py-2 font-semibold text-xs transition-all duration-200",
              "bg-slate-700 text-slate-100 hover:bg-slate-600 border border-slate-600/50",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "focus:ring-2 focus:ring-slate-500/40 focus:outline-none"
            )}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="mr-1 h-3.5 w-3.5" />
                Start
              </>
            )}
          </Button>
        )}

        {status === "processing" && (
          <Button
            type="button"
            disabled
            className="w-full rounded-lg bg-slate-700/50 text-slate-300 font-semibold text-xs border border-slate-600/40 px-3 py-2"
          >
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin text-slate-400" />
            In progress
          </Button>
        )}

        {status === "completed" && (
          <Button
            type="button"
            onClick={handleViewReport}
            className="w-full rounded-lg bg-emerald-700 text-white font-semibold text-xs transition-all duration-200 hover:bg-emerald-600 border border-emerald-600/50 focus:ring-2 focus:ring-emerald-500/40 focus:outline-none px-3 py-2"
          >
            <Eye className="mr-1 h-3.5 w-3.5" />
            View
          </Button>
        )}

        {status === "failed" && (
          <Button
            type="button"
            onClick={handleRetry}
            className="w-full rounded-lg bg-rose-500 text-white font-semibold text-xs transition-all duration-200 hover:bg-rose-400 border border-rose-500/50 focus:ring-2 focus:ring-rose-400/40 focus:outline-none px-3 py-2"
          >
            <RotateCcw className="mr-1 h-3.5 w-3.5" />
            Retry
          </Button>
        )}
      </td>
    </tr>
  );
}
