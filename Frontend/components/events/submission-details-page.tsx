"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  GitBranch,
  Loader2,
  MonitorPlay,
  Paperclip,
  XCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { WorkerSubmissionDetail, RunStatus } from "@/lib/types";
import {
  fetchWorkerSubmission,
  startWorkerSubmissionProcessing,
} from "@/lib/backend-submissions";
import { ResultsPanel } from "@/components/analyze/results-panel";
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

function normalizeDemoScore(score: string | undefined): string {
  if (!score) return "";
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

function scoreTone(value: number | null) {
  if (value === null) return "text-muted-foreground";
  if (value >= 4) return "text-emerald-300";
  if (value >= 2.5) return "text-amber-300";
  return "text-red-300";
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
  const [detail, setDetail] = useState<WorkerSubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("repository");

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

  async function startProcessing() {
    if (!detail) return;

    setStarting(true);
    setError(null);

    try {
      await startWorkerSubmissionProcessing({ submissionId: detail.id });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start processing.");
    } finally {
      setStarting(false);
    }
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

  const statusConfig: Record<
    RunStatus,
    {
      label: string;
      hint: string;
      badgeClass: string;
      icon: React.ReactNode;
      progress: number;
    }
  > = {
    submitted: {
      label: "Submitted",
      hint: "Files were uploaded and are ready for analysis.",
      badgeClass: "bg-slate-500/15 text-slate-200 border-slate-400/20",
      icon: <Clock3 className="h-4 w-4" />,
      progress: 10,
    },
    queued: {
      label: "Processing",
      hint: "Queued and waiting for the worker to start.",
      badgeClass: "bg-violet-500/15 text-violet-200 border-violet-400/20",
      icon: <Loader2 className="h-4 w-4 animate-spin" />,
      progress: 30,
    },
    running: {
      label: "Processing",
      hint: "Analyzing repository, presentation, and demo artifacts.",
      badgeClass: "bg-violet-500/15 text-violet-200 border-violet-400/20",
      icon: <Loader2 className="h-4 w-4 animate-spin" />,
      progress: 65,
    },
    completed: {
      label: "Completed",
      hint: "Analysis is complete and feedback is ready to review.",
      badgeClass: "bg-emerald-500/15 text-emerald-200 border-emerald-400/20",
      icon: <CheckCircle2 className="h-4 w-4" />,
      progress: 100,
    },
    failed: {
      label: "Failed",
      hint: "Processing stopped. Review errors and retry if needed.",
      badgeClass: "bg-rose-500/15 text-rose-200 border-rose-400/20",
      icon: <XCircle className="h-4 w-4" />,
      progress: 100,
    },
  };

  const activeStatus = statusConfig[displayStatus ?? "submitted"];

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

  const finalScore =
    average(
      (detail?.feedback?.scores ?? [])
        .map((row) => row.score)
        .filter((value) => Number.isFinite(value)),
    ) ?? null;

  const canStartProcessing =
    !starting &&
    Boolean(detail) &&
    displayStatus !== "queued" &&
    displayStatus !== "running" &&
    displayStatus !== "completed";

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
              {starting ? "Starting processing..." : "Start Processing"}
            </button>
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
            <section className="rounded-3xl border border-slate-800/60 bg-slate-900/70 p-5 shadow-xl shadow-black/20 backdrop-blur-md md:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold shadow-sm",
                        activeStatus.badgeClass,
                      )}
                    >
                      {activeStatus.icon}
                    </span>

                    {(displayStatus === "queued" || displayStatus === "running") && (
                      <span className="inline-flex items-center gap-1.5 text-xs text-slate-400">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        AI analysis running
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    <h2 className="text-lg font-semibold text-white">
                      Live Submission Status
                    </h2>

                    <p className="max-w-2xl text-sm leading-6 text-slate-300">
                      {activeStatus.hint}
                    </p>
                  </div>
                </div>

                <div className="flex flex-col items-end">
                  <span className="text-xs uppercase tracking-wider text-slate-500">
                    Progress
                  </span>
                  <span className="mt-1 text-lg font-semibold text-white">
                    {activeStatus.progress}%
                  </span>
                </div>
              </div>

              <div className="mt-5 h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 via-violet-500 to-emerald-400 transition-all duration-700"
                  style={{ width: `${activeStatus.progress}%` }}
                />
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {displayStatus === "submitted" && (
                  <span className="rounded-full border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs text-slate-300">
                    Waiting for analysis
                  </span>
                )}

                {(displayStatus === "queued" || displayStatus === "running") && (
                  <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs text-violet-200">
                    AI pipeline active
                  </span>
                )}

                {displayStatus === "completed" && (
                  <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">
                    Feedback ready
                  </span>
                )}

                {displayStatus === "failed" && (
                  <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-200">
                    Needs retry
                  </span>
                )}
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <ResultSummaryCard
                title="PPT Feedback"
                description={
                  ppt?.error
                    ? ppt.error
                    : ppt?.skipped
                      ? ppt.reason ?? "Presentation analysis was skipped."
                      : ppt?.ppt_summary ?? "No presentation analysis yet."
                }
                value={pptScore !== null ? `${pptScore.toFixed(1)}/5` : "Pending"}
                valueClassName={scoreTone(pptScore)}
              />

              <ResultSummaryCard
                title="Repository Feedback"
                description={
                  repoError ??
                  (repoAnalysis?.executive_summary ??
                    "Repository analysis summary will appear here.")
                }
                value={repoError ? "Failed" : repoAnalysis ? "Ready" : "Pending"}
                valueClassName={
                  repoError
                    ? "text-red-300"
                    : repoAnalysis
                      ? "text-emerald-300"
                      : "text-muted-foreground"
                }
              />

              <ResultSummaryCard
                title="Demo Feedback"
                description={
                  video?.error
                    ? video.error
                    : video?.skipped
                      ? video.reason ?? "Demo analysis was skipped."
                      : video?.parsed?.summary ?? "No demo analysis yet."
                }
                value={demoScore !== null ? `${demoScore.toFixed(1)}/5` : "Pending"}
                valueClassName={scoreTone(demoScore)}
              />

              <ResultSummaryCard
                title="Final Grade Summary"
                description={
                  detail.feedback?.summary ??
                  "Final grade summary will be shown once processing is completed."
                }
                value={finalScore !== null ? `${finalScore.toFixed(1)} avg` : "Pending"}
                valueClassName={scoreTone(finalScore)}
              />
            </section>

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

            {activeTab === "repository" ? (
              repoError ? (
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

            {activeTab === "presentation" ? (
              <section className="space-y-4 rounded-[1.75rem] border border-border/70 bg-card/70 p-6 md:p-7">
                <h2 className="text-lg font-semibold text-white">Presentation</h2>

                {!ppt ? (
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
                      <div className="rounded-2xl border border-border/70 bg-background/30 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                          Summary
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-foreground/90">
                          {ppt.ppt_summary}
                        </p>
                      </div>
                    ) : null}

                    {ppt.criteria_scores && ppt.criteria_scores.length > 0 ? (
                      <div className="rounded-2xl border border-border/70 bg-background/30 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                          Rubric
                        </p>
                        <div className="mt-3 overflow-auto rounded-xl border border-border/70">
                          <table className="w-full min-w-[520px] border-collapse text-left text-[12px]">
                            <thead>
                              <tr className="border-b border-border/70 bg-card/70">
                                <th className="px-3 py-2 font-medium text-muted-foreground">Criterion</th>
                                <th className="px-3 py-2 font-medium text-muted-foreground">Score (0–5)</th>
                                <th className="px-3 py-2 font-medium text-muted-foreground">Comment</th>
                              </tr>
                            </thead>
                            <tbody>
                              {ppt.criteria_scores.map((row, idx) => {
                                const meta = labelForPptCriterion(row.category);
                                const label = meta?.label ?? row.category;

                                return (
                                  <tr
                                    key={`${row.category}-${idx}`}
                                    className="border-b border-border/50 last:border-0"
                                  >
                                    <td className="px-3 py-2 text-foreground/90">
                                      <div className="font-medium text-foreground/90">{label}</div>
                                    </td>
                                    <td className="px-3 py-2 text-foreground/90 tabular-nums">
                                      {normalizePptScore(row.score)}
                                    </td>
                                    <td className="px-3 py-2 text-muted-foreground">
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

            {activeTab === "demo" ? (
              <section className="space-y-4 rounded-[1.75rem] border border-border/70 bg-card/70 p-6 md:p-7">
                <h2 className="text-lg font-semibold text-white">Demo video</h2>

                {!video ? (
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
                      <div className="rounded-2xl border border-border/70 bg-background/30 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                          Summary
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-foreground/90">
                          {video.parsed.summary}
                        </p>
                      </div>
                    ) : null}

                    {video.parsed?.limitations ? (
                      <p className="text-sm text-muted-foreground">
                        <span className="font-semibold text-foreground/90">Limitations:</span>{" "}
                        {video.parsed.limitations}
                      </p>
                    ) : null}

                    {video.parsed?.rubric && video.parsed.rubric.length > 0 ? (
                      <div className="rounded-2xl border border-border/70 bg-background/30 p-5">
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
                          Rubric
                        </p>
                        <div className="mt-3 overflow-auto rounded-xl border border-border/70">
                          <table className="w-full min-w-[640px] border-collapse text-left text-[12px]">
                            <thead>
                              <tr className="border-b border-border/70 bg-card/70">
                                <th className="px-3 py-2 font-medium text-muted-foreground">Criterion</th>
                                <th className="px-3 py-2 font-medium text-muted-foreground">Score (0–5)</th>
                                <th className="px-3 py-2 font-medium text-muted-foreground">Evidence</th>
                                <th className="px-3 py-2 font-medium text-muted-foreground">Time</th>
                              </tr>
                            </thead>
                            <tbody>
                              {video.parsed.rubric.map((row, idx) => {
                                const meta = labelForDemoCriterion(row.id);
                                const label = meta?.label ?? row.id ?? "";

                                return (
                                  <tr
                                    key={`${row.id ?? "row"}-${idx}`}
                                    className="border-b border-border/50 last:border-0"
                                  >
                                    <td className="px-3 py-2 text-foreground/90">
                                      <div className="font-medium text-foreground/90">{label}</div>
                                    </td>
                                    <td className="px-3 py-2 text-foreground/90 tabular-nums">
                                      {normalizeDemoScore(row.score)}
                                    </td>
                                    <td className="px-3 py-2 text-muted-foreground">
                                      {row.evidence ?? ""}
                                    </td>
                                    <td className="px-3 py-2 text-muted-foreground">
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
              <section className="space-y-4 rounded-[1.75rem] border border-border/70 bg-card/70 p-6 md:p-7">
                <h2 className="text-lg font-semibold text-white">Artifacts</h2>

                {detail.artifacts.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No artifacts uploaded.</p>
                ) : (
                  <div className="space-y-2">
                    {detail.artifacts.map((a) => (
                      <div
                        key={a.id}
                        className="rounded-2xl border border-border/70 bg-background/30 px-4 py-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-medium text-foreground/90">
                            {a.file_name ?? a.object_key}
                          </p>
                          <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] font-semibold text-neutral-300">
                            {a.kind}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Status: {a.status}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </section>
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

function ResultSummaryCard({
  title,
  description,
  value,
  valueClassName,
}: {
  title: string;
  description: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <article className="rounded-2xl border border-border/70 bg-card/70 p-4 shadow-md shadow-black/10">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        {title}
      </p>
      <p className={cn("mt-2 text-2xl font-semibold tracking-tight", valueClassName)}>
        {value}
      </p>
      <p className="mt-2 line-clamp-4 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </article>
  );
}