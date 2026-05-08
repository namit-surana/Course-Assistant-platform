"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ExternalLink,
  FileText,
  GitBranch,
  Loader2,
  MonitorPlay,
  Paperclip,
  X,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { WorkerSubmissionDetail, RunStatus } from "@/lib/types";
import {
  fetchWorkerSubmission,
  startWorkerSubmissionFinalGrading,
  startWorkerSubmissionGitAnalysis,
  startWorkerSubmissionPptAnalysis,
  startWorkerSubmissionVideoAnalysis,
} from "@/lib/backend-submissions";
import { ResultsPanel } from "@/components/analyze/results-panel";
import { GitAnalysisProgress } from "@/components/events/git-analysis-progress";
import {
  labelForDemoCriterion,
  labelForPptCriterion,
} from "@/lib/builtin-rubric-labels";

type TabId = "repository" | "presentation" | "demo" | "artifacts";

function shortRepo(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
}

function normalizePptScore(score: number): string {
  if (!Number.isFinite(score)) return "";
  const scaled = score >= 0 && score <= 1 ? score * 5 : score;
  const clamped = Math.max(0, Math.min(5, scaled));
  const rounded = Math.round(clamped * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function normalizeDemoScore(score: string | number | null | undefined): string {
  if (score === null || score === undefined) return "";
  if (typeof score === "number") {
    if (!Number.isFinite(score)) return "";
    const clamped = Math.max(0, Math.min(5, score));
    const rounded = Math.round(clamped * 10) / 10;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  }

  const raw = score.trim();
  const asNum = Number(raw);

  if (Number.isFinite(asNum)) {
    const clamped = Math.max(0, Math.min(5, asNum));
    return Number.isInteger(clamped) ? String(clamped) : String(clamped);
  }

  const map: Record<string, number> = {
    exceeds: 5,
    excellent: 5,
    strong: 5,
    meets: 4,
    good: 4,
    partial: 2,
    "partially meets": 2,
    "needs improvement": 2,
    weak: 1,
    poor: 1,
    fails: 0,
    fail: 0,
  };

  const hit = map[raw.toLowerCase()];
  if (hit !== undefined) return String(hit);
  return "";
}

function statusPill(status: RunStatus) {
  const base =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold";

  if (status === "submitted")
    return <span className={cn(base, "bg-neutral-800 text-neutral-300")}>Submitted</span>;

  if (status === "queued")
    return <span className={cn(base, "bg-neutral-800 text-neutral-300")}>Queued</span>;

  if (status === "running")
    return <span className={cn(base, "bg-violet-500/15 text-violet-200")}>Running</span>;

  if (status === "completed")
    return <span className={cn(base, "bg-emerald-500/15 text-emerald-200")}>Completed</span>;

  return <span className={cn(base, "bg-red-500/15 text-red-200")}>Failed</span>;
}

function tabBadge(kind: "ok" | "running" | "missing" | "failed") {
  if (kind === "ok") return <span className="ml-2 h-1.5 w-1.5 rounded-full bg-emerald-400" />;
  if (kind === "running") return <span className="ml-2 h-1.5 w-1.5 rounded-full bg-violet-400" />;
  if (kind === "failed") return <span className="ml-2 h-1.5 w-1.5 rounded-full bg-red-400" />;
  return <span className="ml-2 h-1.5 w-1.5 rounded-full bg-neutral-600" />;
}

function average(values: number[]) {
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function SubmissionDetailsPage({
  eventId,
  submissionId,
}: {
  eventId: string;
  submissionId: string;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isDemoView = searchParams.get("demo") === "1";
  const [detail, setDetail] = useState<WorkerSubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [startingFinal, setStartingFinal] = useState(false);
  const [gitRunId, setGitRunId] = useState<string | null>(null);
  const [pptRunId, setPptRunId] = useState<string | null>(null);
  const [videoRunId, setVideoRunId] = useState<string | null>(null);
  const [finalRunId, setFinalRunId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("repository");
  const [showDeepAnalysis, setShowDeepAnalysis] = useState(false);
  const [showStatusPanel, setShowStatusPanel] = useState(false);
  const [isLiveDemoRunning, setIsLiveDemoRunning] = useState(false);
  const [liveDemoStep, setLiveDemoStep] = useState(0);
  const [liveDemoFeed, setLiveDemoFeed] = useState<string[]>([]);
  const [liveDemoElapsedSeconds, setLiveDemoElapsedSeconds] = useState(0);
  const liveDemoTimersRef = useRef<number[]>([]);
  const hasAutoStartedDemoRef = useRef(false);

  async function refresh() {
    try {
      const loaded = await fetchWorkerSubmission(submissionId);
      setDetail(loaded);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load submission.");
    }
  }

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submissionId]);

  useEffect(() => {
    if (!detail) return;
    if (detail.status !== "queued" && detail.status !== "running") return;

    const id = window.setInterval(() => {
      void refresh();
    }, 2000);

    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.status, submissionId]);

  const repositoryResult = detail?.feedback?.raw_result?.repository;
  const repoAnalysis = repositoryResult?.repository_analysis;
  const repoError = repositoryResult?.error;

  const displayStatus: RunStatus | undefined =
    detail?.status === "completed" && repoError && !repoAnalysis
      ? "failed"
      : detail?.status;

  const ppt = detail?.feedback?.raw_result?.ppt ?? null;
  const video = detail?.feedback?.raw_result?.video ?? null;
  const finalReport = detail?.feedback?.raw_result?.final_grading ?? null;
  const finalGradingStatus = detail?.feedback?.raw_result?.final_grading_status?.status;
  const finalGradingError = detail?.feedback?.raw_result?.final_grading_status?.error;

  useEffect(() => {
    if (detail?.feedback?.raw_result?.final_grading) {
      setFinalRunId(null);
    }
  }, [detail?.feedback?.raw_result?.final_grading]);

  const defaultTab = useMemo<TabId>(() => {
    const hasVideo = Boolean(video && !video.skipped && !video.error);
    const hasPpt = Boolean(ppt && !ppt.skipped && !ppt.error);

    if (hasVideo) return "demo";
    if (hasPpt) return "presentation";
    return "repository";
  }, [ppt, video]);

  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab]);

  useEffect(() => {
    hasAutoStartedDemoRef.current = false;
  }, [submissionId]);

  async function startProcessing() {
    if (!detail) return;

    setStarting(true);
    setError(null);

    try {
      const startTasks: Array<{
        label: string;
        start: () => Promise<unknown>;
      }> = [];

      if (detail.repo_url) {
        startTasks.push({
          label: "repository",
          start: async () => {
            const result = await startWorkerSubmissionGitAnalysis({ submissionId: detail.id });
            if (result.run_id) {
              setGitRunId(result.run_id);
            }
            return result;
          },
        });
      }

      if (detail.artifacts.some((artifact) => artifact.kind === "ppt")) {
        startTasks.push({
          label: "presentation",
          start: async () => {
            const result = await startWorkerSubmissionPptAnalysis({ submissionId: detail.id });
            if (result.run_id) {
              setPptRunId(result.run_id);
            }
            return result;
          },
        });
      }

      if (detail.artifacts.some((artifact) => artifact.kind === "video")) {
        startTasks.push({
          label: "video",
          start: async () => {
            const result = await startWorkerSubmissionVideoAnalysis({ submissionId: detail.id });
            if (result.run_id) {
              setVideoRunId(result.run_id);
            }
            return result;
          },
        });
      }

      if (startTasks.length === 0) {
        throw new Error("No repository, presentation, or video artifact available to analyze.");
      }

      const settled = await Promise.allSettled(startTasks.map((task) => task.start()));
      const failures = settled.flatMap((result, index) => {
        if (result.status === "fulfilled") return [];
        const message = result.reason instanceof Error ? result.reason.message : "Unknown error";
        return [`${startTasks[index]?.label ?? "analysis"}: ${message}`];
      });

      if (failures.length === settled.length) {
        throw new Error(failures.join(" | "));
      }

      await refresh();
      if (failures.length > 0) {
        setError(`Some analyses could not start: ${failures.join(" | ")}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start analyses.");
    } finally {
      setStarting(false);
    }
  }

  async function startFinalGrading() {
    if (!detail) return;
    setStartingFinal(true);
    setError(null);
    try {
      const started = await startWorkerSubmissionFinalGrading({ submissionId: detail.id });
      if (started.run_id) {
        setFinalRunId(started.run_id);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start final grading.");
    } finally {
      setStartingFinal(false);
    }
  }

  function clearLiveDemoTimers() {
    for (const timer of liveDemoTimersRef.current) {
      window.clearTimeout(timer);
    }
    liveDemoTimersRef.current = [];
  }

  function pushLiveDemoEvent(message: string, step: number) {
    setLiveDemoFeed((prev) => [...prev, message]);
    setLiveDemoStep(step);
  }

  function startLiveDemoReplay() {
    if (!detail) return;
    clearLiveDemoTimers();
    setIsLiveDemoRunning(true);
    setLiveDemoStep(0);
    setLiveDemoFeed([]);
    setLiveDemoElapsedSeconds(0);
    setShowDeepAnalysis(true);

    const baseEvents: Array<{ at: number; message: string; step: number }> = [
      { at: 1500, message: "Queued for analysis...", step: 0 },
      { at: 7000, message: "Repository analysis started", step: 1 },
      { at: 16500, message: "Repository analysis completed", step: 2 },
      { at: 23000, message: "Presentation analysis started", step: 3 },
      { at: 32000, message: "Presentation analysis completed", step: 4 },
      { at: 39000, message: "Demo video analysis started", step: 5 },
      { at: 48500, message: "Demo video analysis completed", step: 6 },
      { at: 56000, message: "Final grading started", step: 7 },
      { at: 66000, message: "Final score generated", step: 8 },
    ];

    for (const event of baseEvents) {
      const timer = window.setTimeout(() => {
        pushLiveDemoEvent(event.message, event.step);
      }, event.at);
      liveDemoTimersRef.current.push(timer);
    }

    const criteriaCount = finalReport?.criterion_grades?.length ?? 0;
    const criteriaBaseDelay = 68000;
    for (let index = 0; index < criteriaCount; index += 1) {
      const timer = window.setTimeout(() => {
        const criterionName = finalReport?.criterion_grades?.[index]?.criterion ?? `criterion ${index + 1}`;
        pushLiveDemoEvent(`Final criterion streamed: ${criterionName}`, 9 + index);
      }, criteriaBaseDelay + index * 1800);
      liveDemoTimersRef.current.push(timer);
    }

    const doneDelay = criteriaBaseDelay + criteriaCount * 1800 + 2500;
    const doneTimer = window.setTimeout(() => {
      setLiveDemoFeed((prev) => [...prev, "Replay complete"]);
      setIsLiveDemoRunning(false);
    }, doneDelay);
    liveDemoTimersRef.current.push(doneTimer);
  }

  const repoTabState: "ok" | "running" | "missing" | "failed" =
    displayStatus === "failed" || repoError
      ? "failed"
      : repoAnalysis
        ? "ok"
        : displayStatus === "running" || displayStatus === "queued"
          ? "running"
          : "missing";

  const pptTabState: "ok" | "running" | "missing" | "failed" =
    displayStatus === "failed"
      ? "failed"
      : ppt && !ppt.skipped && !ppt.error
        ? "ok"
        : displayStatus === "running" || displayStatus === "queued"
          ? "running"
          : "missing";

  const videoTabState: "ok" | "running" | "missing" | "failed" =
    displayStatus === "failed"
      ? "failed"
      : video && !video.skipped && !video.error
        ? "ok"
        : displayStatus === "running" || displayStatus === "queued"
          ? "running"
          : "missing";

  const pptScore =
    average(
      (ppt?.criteria_scores ?? [])
        .map((row) => {
          const value = Number(normalizePptScore(row.score));
          return Number.isFinite(value) ? value : NaN;
        })
        .filter((value) => Number.isFinite(value)),
    ) ?? null;

  const demoScore =
    average(
      (video?.parsed?.rubric ?? [])
        .map((row) => Number(normalizeDemoScore(row.score)))
        .filter((value) => Number.isFinite(value)),
    ) ?? null;

  const showRepoStreamData = !isLiveDemoRunning || liveDemoStep >= 2;
  const showPptStreamData = !isLiveDemoRunning || liveDemoStep >= 4;
  const showVideoStreamData = !isLiveDemoRunning || liveDemoStep >= 6;
  const showFinalScore = !isLiveDemoRunning || liveDemoStep >= 8;
  const finalScore = finalReport?.overall_score ?? null;
  const finalMaxScore = finalReport?.overall_max_score ?? null;
  const finalScoreLabel =
    showFinalScore && finalScore !== null && finalMaxScore !== null
      ? `${finalScore.toFixed(1)}/${finalMaxScore.toFixed(1)}`
      : "Pending";
  const streamedCriterionCount = isLiveDemoRunning ? Math.max(0, liveDemoStep - 8) : undefined;
  const visibleCriterionRows = finalReport?.criterion_grades
    ? finalReport.criterion_grades.slice(
        0,
        streamedCriterionCount === undefined
          ? finalReport.criterion_grades.length
          : Math.min(streamedCriterionCount, finalReport.criterion_grades.length),
      )
    : [];
  const liveFeedTotalSteps = 5;
  const liveFeedCurrentStep =
    liveDemoStep >= 7 ? 5 : liveDemoStep >= 5 ? 4 : liveDemoStep >= 3 ? 3 : liveDemoStep >= 1 ? 2 : 1;
  const liveFeedHeaderState = isLiveDemoRunning
    ? `Running • Step ${liveFeedCurrentStep}/${liveFeedTotalSteps} • ${Math.floor(
        liveDemoElapsedSeconds / 60,
      )
        .toString()
        .padStart(2, "0")}:${(liveDemoElapsedSeconds % 60).toString().padStart(2, "0")} elapsed`
    : liveDemoFeed.length > 0
      ? "Completed"
      : "Idle";

  const liveFeedPhases: Array<{
    label: string;
    detail: string;
    state: "waiting" | "running" | "done";
  }> = [
    {
      label: "Queued",
      detail: "Queued for analysis...",
      state: liveDemoFeed.length > 0 || liveDemoStep >= 1 ? "done" : isLiveDemoRunning ? "running" : "waiting",
    },
    {
      label: "Repository analysis",
      detail: "Repository analysis started",
      state: liveDemoStep >= 2 ? "done" : liveDemoStep >= 1 && isLiveDemoRunning ? "running" : "waiting",
    },
    {
      label: "Presentation analysis",
      detail: "Presentation analysis started",
      state: liveDemoStep >= 4 ? "done" : liveDemoStep >= 3 && isLiveDemoRunning ? "running" : "waiting",
    },
    {
      label: "Demo video analysis",
      detail: "Demo video analysis started",
      state: liveDemoStep >= 6 ? "done" : liveDemoStep >= 5 && isLiveDemoRunning ? "running" : "waiting",
    },
    {
      label: "Final grading",
      detail: "Final grading started",
      state: liveDemoStep >= 8 ? "done" : liveDemoStep >= 7 && isLiveDemoRunning ? "running" : "waiting",
    },
  ];
  const currentLiveMessage = liveDemoFeed[liveDemoFeed.length - 1] ?? "Waiting for next update...";

  const showRealActionButtons = true;
  const showLiveDemoButton = false;

  const canStartProcessing =
    !starting &&
    Boolean(detail) &&
    displayStatus !== "queued" &&
    displayStatus !== "running";
  const finalJobRunning = finalGradingStatus === "queued" || finalGradingStatus === "running";
  const showFinalGradingSkeleton =
    !finalReport && !finalGradingError && (finalJobRunning || Boolean(finalRunId));
  const canRunFinalNow =
    !startingFinal &&
    !finalRunId &&
    Boolean(detail) &&
    !finalJobRunning &&
    displayStatus !== "queued" &&
    displayStatus !== "running";

  useEffect(() => {
    return () => {
      clearLiveDemoTimers();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isLiveDemoRunning) return;
    const timer = window.setInterval(() => {
      setLiveDemoElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isLiveDemoRunning]);

  // Demo replay auto-start is intentionally disabled so the real in-process
  // git-analysis progress (via /runs/{id}) drives the UI. Re-enable by
  // restoring the effect below if you need the canned replay again.
  // useEffect(() => {
  //   if (!isDemoView || !detail) return;
  //   if (hasAutoStartedDemoRef.current) return;
  //   hasAutoStartedDemoRef.current = true;
  //   startLiveDemoReplay();
  // }, [isDemoView, detail]);

  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-0 z-30 border-b border-neutral-800/60 bg-background/80 backdrop-blur-md">
        <div className="w-full px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                if (window.history.length > 1) {
                  router.back();
                } else {
                  router.push(`/events/${eventId}`);
                }
              }}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-neutral-800 text-neutral-400 transition-colors hover:bg-neutral-800 hover:text-white"
              title="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-sm font-semibold text-white sm:text-base">
                  {detail?.team_name ?? "Submission"}
                </h1>
                {displayStatus ? statusPill(displayStatus) : null}
                {finalGradingStatus && finalGradingStatus !== displayStatus
                  ? statusPill(finalGradingStatus as RunStatus)
                  : null}
              </div>

              <div className="mt-0.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-500">
                {detail?.repo_url ? (
                  <a
                    href={detail.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 hover:text-violet-300"
                  >
                    <GitBranch className="h-3 w-3" />
                    <span className="truncate">{shortRepo(detail.repo_url)}</span>
                    <ExternalLink className="h-3 w-3 text-neutral-600" />
                  </a>
                ) : null}

                {detail?.updated_at ? (
                  <span>Last update: {new Date(detail.updated_at).toLocaleString()}</span>
                ) : null}
              </div>
            </div>

            {showRealActionButtons ? (
              <button
                type="button"
                onClick={() => void startProcessing()}
                disabled={!canStartProcessing}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-white transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/60 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  canStartProcessing
                    ? "bg-emerald-600 shadow-sm shadow-emerald-900/30 hover:-translate-y-0.5 hover:bg-emerald-500"
                    : "cursor-not-allowed bg-emerald-700/40 text-emerald-100/70",
                )}
              >
                {starting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {starting ? "Starting analyses..." : "Start Analysis"}
              </button>
            ) : null}
            {showRealActionButtons ? (
              <button
                type="button"
                onClick={() => void startFinalGrading()}
                disabled={!canRunFinalNow}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold text-white transition-all",
                  canRunFinalNow
                    ? "bg-violet-600 shadow-sm shadow-violet-900/30 hover:-translate-y-0.5 hover:bg-violet-500"
                    : "cursor-not-allowed bg-violet-700/40 text-violet-100/70",
                )}
              >
                {startingFinal ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {startingFinal ? "Starting final grading..." : "Run Final Grade Now"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setShowDeepAnalysis(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-neutral-700 bg-neutral-900/80 px-4 py-2 text-xs font-semibold text-neutral-100 transition-all hover:-translate-y-0.5 hover:border-violet-500/60 hover:text-white"
            >
              View Deep Analysis
            </button>
            <button
              type="button"
              onClick={() => setShowStatusPanel(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-neutral-700 bg-neutral-900/80 px-4 py-2 text-xs font-semibold text-neutral-100 transition-all hover:-translate-y-0.5 hover:border-neutral-500/80 hover:text-white"
            >
              Status
            </button>
            {showLiveDemoButton ? (
              <button
                type="button"
                onClick={() => startLiveDemoReplay()}
                disabled={!detail || isLiveDemoRunning}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-semibold transition-all",
                  !detail || isLiveDemoRunning
                    ? "cursor-not-allowed border-cyan-700/40 bg-cyan-900/20 text-cyan-200/60"
                    : "border-cyan-500/40 bg-cyan-500/15 text-cyan-100 hover:-translate-y-0.5 hover:border-cyan-400/70 hover:text-white",
                )}
              >
                {isLiveDemoRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {isLiveDemoRunning ? "Streaming Replay..." : "Live Demo"}
              </button>
            ) : null}
          </div>

          {error ? <p className="mt-2 text-xs text-red-400">{error}</p> : null}
        </div>
      </div>

      <div className="w-full space-y-5 px-4 py-6 sm:px-6">
        {!detail ? (
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950/40 px-4 py-12 text-center">
            <Loader2 className="mx-auto h-5 w-5 animate-spin text-neutral-500" />
            <p className="mt-3 text-sm text-neutral-400">Loading submission…</p>
          </div>
        ) : (
          <>
            <section className="space-y-4 rounded-[1.75rem] border border-neutral-700/70 bg-neutral-900/80 p-6 md:p-7">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <h2 className="text-lg font-semibold text-white">Final grader report</h2>
                <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-3 py-2 text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200/90">
                    Final score
                  </p>
                  <p
                    className={cn(
                      "text-base font-semibold tabular-nums",
                      finalScoreLabel === "Pending" ? "text-neutral-200" : "text-cyan-100",
                    )}
                  >
                    {finalScoreLabel}
                  </p>
                </div>
              </div>
              {finalRunId ? (
                <GitAnalysisProgress
                  runId={finalRunId}
                  collapsible
                  collapseOnComplete
                  onCompleted={() => {
                    setFinalRunId(null);
                    void refresh();
                  }}
                />
              ) : null}
              {!finalReport ? (
                <>
                  {finalGradingError ? (
                    <p className="text-sm text-neutral-300">{`Final grading failed: ${finalGradingError}`}</p>
                  ) : showFinalGradingSkeleton ? (
                    <div className="space-y-4">
                      <div className="space-y-2">
                        <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-700/70" />
                        <div className="h-3 w-5/6 animate-pulse rounded bg-neutral-700/70" />
                        <div className="h-3 w-3/4 animate-pulse rounded bg-neutral-700/70" />
                      </div>
                      <div className="overflow-auto rounded-xl border border-neutral-600/70">
                        <table className="w-full min-w-[640px] border-collapse text-left text-[13px]">
                          <thead>
                            <tr className="border-b border-neutral-600/70 bg-violet-500/10">
                              <th className="px-3 py-2.5 font-medium text-neutral-200">Criterion</th>
                              <th className="px-3 py-2.5 font-medium text-neutral-200">Score</th>
                              <th className="px-3 py-2.5 font-medium text-neutral-200">Reasoning</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Array.from({ length: 5 }, (_, idx) => (
                              <tr
                                key={`final-skel-${idx}`}
                                className={cn(
                                  "border-b border-neutral-700/70 last:border-0",
                                  idx % 2 === 0 ? "bg-neutral-900/30" : "bg-neutral-900/55",
                                )}
                              >
                                <td className="px-3 py-2.5">
                                  <div className="h-3 max-w-[200px] w-4/5 animate-pulse rounded bg-neutral-700/60" />
                                </td>
                                <td className="px-3 py-2.5">
                                  <div className="h-3 w-16 animate-pulse rounded bg-neutral-700/60" />
                                </td>
                                <td className="px-3 py-2.5">
                                  <div className="h-3 max-w-md w-full animate-pulse rounded bg-neutral-700/50" />
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-300">
                      Final grader output will appear once the final grading job completes.
                    </p>
                  )}
                </>
              ) : (
                <>
                  {showFinalScore ? (
                    <p className="text-sm leading-7 text-neutral-100">{finalReport.overall_reasoning}</p>
                  ) : (
                    <div className="space-y-2">
                      <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-700/70" />
                      <div className="h-3 w-5/6 animate-pulse rounded bg-neutral-700/70" />
                      <div className="h-3 w-3/4 animate-pulse rounded bg-neutral-700/70" />
                    </div>
                  )}
                  {finalReport.criterion_grades && finalReport.criterion_grades.length > 0 ? (
                    <div className="overflow-auto rounded-xl border border-neutral-600/70">
                      <table className="w-full min-w-[640px] border-collapse text-left text-[13px]">
                        <thead>
                          <tr className="border-b border-neutral-600/70 bg-violet-500/10">
                            <th className="px-3 py-2.5 font-medium text-neutral-200">Criterion</th>
                            <th className="px-3 py-2.5 font-medium text-neutral-200">Score</th>
                            <th className="px-3 py-2.5 font-medium text-neutral-200">Reasoning</th>
                          </tr>
                        </thead>
                        <tbody>
                          {visibleCriterionRows.map((row, idx) => (
                            <tr
                              key={`${row.criterion}-${idx}`}
                              className={cn(
                                "border-b border-neutral-700/70 last:border-0 hover:bg-violet-500/10 transition-colors",
                                idx % 2 === 0 ? "bg-neutral-900/30" : "bg-neutral-900/55"
                              )}
                            >
                              <td className="px-3 py-2.5 text-neutral-100">{row.criterion}</td>
                              <td
                                className={cn(
                                  "px-3 py-2.5 tabular-nums font-semibold",
                                  row.max_score > 0 && row.score / row.max_score >= 0.75
                                    ? "text-emerald-300"
                                    : row.max_score > 0 && row.score / row.max_score >= 0.4
                                      ? "text-amber-300"
                                      : "text-red-300"
                                )}
                              >
                                {row.score}/{row.max_score}
                              </td>
                              <td className="px-3 py-2.5 text-neutral-300 leading-6">{row.reasoning}</td>
                            </tr>
                          ))}
                          {isLiveDemoRunning &&
                          finalReport.criterion_grades.length > visibleCriterionRows.length ? (
                            <tr className="border-b border-neutral-700/70 bg-neutral-900/40">
                              <td className="px-3 py-2.5 text-neutral-400">Streaming next criterion…</td>
                              <td className="px-3 py-2.5 text-neutral-400 tabular-nums">—</td>
                              <td className="px-3 py-2.5 text-neutral-500">Waiting for next step</td>
                            </tr>
                          ) : null}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </>
              )}
            </section>

            {showDeepAnalysis ? (
              <div
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm sm:p-6"
                onClick={() => setShowDeepAnalysis(false)}
              >
                <div
                  className="h-[88vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-neutral-700 bg-background p-5 shadow-2xl shadow-black/40 sm:p-6"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-white">Deep Analysis</h3>
                    <button
                      type="button"
                      onClick={() => setShowDeepAnalysis(false)}
                      className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-neutral-700 text-neutral-300 hover:bg-neutral-800 hover:text-white"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <TabButton
                      active={activeTab === "repository"}
                      onClick={() => setActiveTab("repository")}
                      icon={<GitBranch className="h-4 w-4" />}
                    >
                      Repository {tabBadge(repoTabState)}
                    </TabButton>

                    <TabButton
                      active={activeTab === "presentation"}
                      onClick={() => setActiveTab("presentation")}
                      icon={<FileText className="h-4 w-4" />}
                    >
                      Presentation {tabBadge(pptTabState)}
                    </TabButton>

                    <TabButton
                      active={activeTab === "demo"}
                      onClick={() => setActiveTab("demo")}
                      icon={<MonitorPlay className="h-4 w-4" />}
                    >
                      Demo video {tabBadge(videoTabState)}
                    </TabButton>

                    <TabButton
                      active={activeTab === "artifacts"}
                      onClick={() => setActiveTab("artifacts")}
                      icon={<Paperclip className="h-4 w-4" />}
                    >
                      Artifacts
                    </TabButton>
                  </div>

                  <div className="mt-4 space-y-4 pb-6">
                    {activeTab === "repository" && gitRunId && !repoAnalysis ? (
                      <GitAnalysisProgress
                        runId={gitRunId}
                        collapsible
                        onCompleted={() => {
                          void refresh();
                        }}
                      />
                    ) : null}

                    {activeTab === "repository" ? (
                      isLiveDemoRunning && !showRepoStreamData ? (
                        <section className="rounded-[1.75rem] border border-neutral-700/70 bg-neutral-900/80 p-6 md:p-7">
                          <h2 className="text-lg font-semibold text-white">Repository</h2>
                          <p className="mt-2 text-sm text-neutral-300">Streaming repository analysis…</p>
                          <div className="mt-4 space-y-2">
                            <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-700/70" />
                            <div className="h-3 w-full animate-pulse rounded bg-neutral-700/70" />
                            <div className="h-3 w-5/6 animate-pulse rounded bg-neutral-700/70" />
                            <div className="h-3 w-3/4 animate-pulse rounded bg-neutral-700/70" />
                          </div>
                        </section>
                      ) : repoError ? (
                        <section className="rounded-[1.75rem] border border-red-500/20 bg-red-500/5 p-6">
                          <h2 className="text-lg font-semibold text-red-100">
                            Repository analysis failed
                          </h2>
                          <p className="mt-2 text-sm leading-7 text-red-200/80">
                            {repoError}
                          </p>
                        </section>
                      ) : (
                        <ResultsPanel analysis={repoAnalysis} hideHeader />
                      )
                    ) : null}

                    {activeTab === "presentation" && pptRunId && !ppt ? (
                      <GitAnalysisProgress
                        runId={pptRunId}
                        collapsible
                        onCompleted={() => {
                          void refresh();
                        }}
                      />
                    ) : null}

                    {activeTab === "presentation" ? (
                      <section className="space-y-4 rounded-[1.75rem] border border-neutral-700/70 bg-neutral-900/80 p-6 md:p-7">
                        <h2 className="text-lg font-semibold text-white">Presentation</h2>

                        {isLiveDemoRunning && !showPptStreamData ? (
                          <div className="space-y-3">
                            <p className="text-sm text-neutral-300">Streaming presentation analysis…</p>
                            <div className="space-y-2">
                              <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-700/70" />
                              <div className="h-3 w-full animate-pulse rounded bg-neutral-700/70" />
                              <div className="h-3 w-5/6 animate-pulse rounded bg-neutral-700/70" />
                            </div>
                          </div>
                        ) : !ppt ? (
                          <p className="text-sm text-muted-foreground">No presentation analysis yet.</p>
                        ) : ppt.error ? (
                          <p className="text-sm text-red-400">{ppt.error}</p>
                        ) : ppt.skipped ? (
                          <p className="text-sm text-muted-foreground">
                            {ppt.reason ?? "Presentation analysis skipped."}
                          </p>
                        ) : (
                          <>
                            {ppt.ppt_summary ? (
                              <div className="rounded-xl bg-neutral-900/40 p-4">
                                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                                  Summary
                                </p>
                                <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-neutral-100">
                                  {ppt.ppt_summary}
                                </p>
                              </div>
                            ) : null}

                            {ppt.criteria_scores && ppt.criteria_scores.length > 0 ? (
                              <div className="rounded-xl bg-neutral-900/40 p-4">
                                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                                  Rubric
                                </p>
                                <div className="mt-3 overflow-auto rounded-xl">
                                  <table className="w-full min-w-[520px] border-collapse text-left text-[13px]">
                                    <thead>
                                      <tr className="border-b border-neutral-700/70 bg-neutral-900/95">
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Criterion</th>
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Score (0–5)</th>
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Comment</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {ppt.criteria_scores.map((row, idx) => {
                                        const meta = labelForPptCriterion(row.category);
                                        const label = meta?.label ?? row.category;

                                        return (
                                          <tr
                                            key={`${row.category}-${idx}`}
                                            className={cn(
                                              "border-b border-neutral-700/60 last:border-0",
                                              idx % 2 === 0 ? "bg-neutral-900/30" : "bg-neutral-900/50"
                                            )}
                                          >
                                            <td className="px-3 py-2.5 text-neutral-100">
                                              <div className="font-medium text-neutral-100">{label}</div>
                                            </td>
                                            <td className="px-3 py-2.5 tabular-nums text-neutral-100">
                                              {normalizePptScore(row.score)}
                                            </td>
                                            <td className="px-3 py-2.5 text-neutral-300 leading-6">
                                              {row.comment ?? ""}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            ) : null}
                          </>
                        )}
                      </section>
                    ) : null}

                    {activeTab === "demo" && videoRunId && !video ? (
                      <GitAnalysisProgress
                        runId={videoRunId}
                        collapsible
                        onCompleted={() => {
                          void refresh();
                        }}
                      />
                    ) : null}

                    {activeTab === "demo" ? (
                      <section className="space-y-4 rounded-[1.75rem] border border-neutral-700/70 bg-neutral-900/80 p-6 md:p-7">
                        <h2 className="text-lg font-semibold text-white">Demo video</h2>

                        {isLiveDemoRunning && !showVideoStreamData ? (
                          <div className="space-y-3">
                            <p className="text-sm text-neutral-300">Streaming demo video analysis…</p>
                            <div className="space-y-2">
                              <div className="h-3 w-2/3 animate-pulse rounded bg-neutral-700/70" />
                              <div className="h-3 w-full animate-pulse rounded bg-neutral-700/70" />
                              <div className="h-3 w-5/6 animate-pulse rounded bg-neutral-700/70" />
                            </div>
                          </div>
                        ) : !video ? (
                          <p className="text-sm text-muted-foreground">No demo video analysis yet.</p>
                        ) : video.error ? (
                          <p className="text-sm text-red-400">{video.error}</p>
                        ) : video.skipped ? (
                          <p className="text-sm text-muted-foreground">
                            {video.reason ?? "Demo analysis skipped."}
                          </p>
                        ) : (
                          <>
                            {video.parsed?.summary ? (
                              <div className="rounded-xl bg-neutral-900/40 p-4">
                                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                                  Summary
                                </p>
                                <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-neutral-100">
                                  {video.parsed.summary}
                                </p>
                              </div>
                            ) : null}

                            {video.parsed?.limitations ? (
                              <p className="text-sm text-neutral-300">
                                <span className="font-semibold text-neutral-100">Limitations:</span>{" "}
                                {video.parsed.limitations}
                              </p>
                            ) : null}

                            {video.parsed?.rubric && video.parsed.rubric.length > 0 ? (
                              <div className="rounded-xl bg-neutral-900/40 p-4">
                                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                                  Rubric
                                </p>
                                <div className="mt-3 overflow-auto rounded-xl">
                                  <table className="w-full min-w-[640px] border-collapse text-left text-[13px]">
                                    <thead>
                                      <tr className="border-b border-neutral-700/70 bg-neutral-900/95">
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Criterion</th>
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Score (0–5)</th>
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Evidence</th>
                                        <th className="px-3 py-2.5 font-medium text-neutral-300">Time</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {video.parsed.rubric.map((row, idx) => {
                                        const meta = labelForDemoCriterion(row.id);
                                        const label = meta?.label ?? row.id ?? "";

                                        return (
                                          <tr
                                            key={`${row.id ?? "row"}-${idx}`}
                                            className={cn(
                                              "border-b border-neutral-700/60 last:border-0",
                                              idx % 2 === 0 ? "bg-neutral-900/30" : "bg-neutral-900/50"
                                            )}
                                          >
                                            <td className="px-3 py-2.5 text-neutral-100">
                                              <div className="font-medium text-neutral-100">{label}</div>
                                            </td>
                                            <td className="px-3 py-2.5 tabular-nums text-neutral-100">
                                              {normalizeDemoScore(row.score)}
                                            </td>
                                            <td className="px-3 py-2.5 text-neutral-300 leading-6">
                                              {row.evidence ?? ""}
                                            </td>
                                            <td className="px-3 py-2.5 text-neutral-300">
                                              {row.timestamps ?? ""}
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            ) : null}
                          </>
                        )}
                      </section>
                    ) : null}

                    {activeTab === "artifacts" ? (
                      <section className="space-y-4 rounded-[1.75rem] border border-neutral-700/70 bg-neutral-900/80 p-6 md:p-7">
                        <h2 className="text-lg font-semibold text-white">Artifacts</h2>

                        {detail.artifacts.length === 0 ? (
                          <p className="text-sm text-muted-foreground">No artifacts uploaded.</p>
                        ) : (
                          <div className="space-y-2">
                            {detail.artifacts.map((a) => (
                              <div key={a.id} className="rounded-xl bg-neutral-900/40 px-4 py-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <p className="text-sm font-medium text-neutral-100">
                                    {a.file_name ?? a.object_key}
                                  </p>
                                  <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] font-semibold text-neutral-300">
                                    {a.kind}
                                  </span>
                                </div>
                                <p className="mt-1 text-xs text-neutral-300">
                                  Status: {a.status}
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </section>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
            {showStatusPanel ? (
              <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" onClick={() => setShowStatusPanel(false)}>
                <aside
                  className="absolute right-0 top-0 h-full w-full max-w-md border-l border-neutral-800 bg-neutral-950 shadow-2xl"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex h-full flex-col">
                    <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
                      <div>
                        <h3 className="text-sm font-semibold text-white">Live status</h3>
                        <p className="mt-0.5 text-xs text-neutral-400">
                          Real-time agent progress for this submission.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowStatusPanel(false)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-neutral-700 text-neutral-300 hover:bg-neutral-800 hover:text-white"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="flex-1 space-y-4 overflow-y-auto p-4">
                      {!gitRunId && !pptRunId && !videoRunId && !finalRunId ? (
                        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 text-sm text-neutral-400">
                          No active runs yet. Click <span className="text-neutral-200">Start Analysis</span> to
                          begin — repository, presentation, and demo video progress will stream here in real time.
                        </div>
                      ) : null}

                      {gitRunId ? (
                        <GitAnalysisProgress
                          runId={gitRunId}
                          collapsible
                          collapseOnComplete
                          onCompleted={() => {
                            void refresh();
                          }}
                        />
                      ) : null}

                      {pptRunId ? (
                        <GitAnalysisProgress
                          runId={pptRunId}
                          collapsible
                          collapseOnComplete
                          onCompleted={() => {
                            void refresh();
                          }}
                        />
                      ) : null}

                      {videoRunId ? (
                        <GitAnalysisProgress
                          runId={videoRunId}
                          collapsible
                          collapseOnComplete
                          onCompleted={() => {
                            void refresh();
                          }}
                        />
                      ) : null}

                      {finalRunId ? (
                        <GitAnalysisProgress
                          runId={finalRunId}
                          collapsible
                          collapseOnComplete
                          onCompleted={() => {
                            setFinalRunId(null);
                            void refresh();
                          }}
                        />
                      ) : null}
                    </div>
                  </div>
                </aside>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition-colors",
        active
          ? "border-violet-500/40 bg-violet-500/10 text-violet-100"
          : "border-neutral-800 bg-neutral-950/40 text-neutral-300 hover:bg-neutral-900",
      )}
    >
      <span className={cn("text-neutral-400", active ? "text-violet-200" : "text-neutral-500")}>
        {icon}
      </span>
      <span className="whitespace-nowrap">{children}</span>
    </button>
  );
}
