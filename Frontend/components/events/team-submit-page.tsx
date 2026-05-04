"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, GitBranch, Loader2, CheckCircle2 } from "lucide-react";
import { submitWorkerProject } from "@/lib/backend-submissions";
import { useEventsStore } from "@/lib/events-store";
import type { Submission } from "@/lib/types";
import { cn } from "@/lib/utils";

export function TeamSubmitPage({ eventId }: { eventId: string }) {
  const event = useEventsStore((s) => s.events.find((e) => e.id === eventId));
  const addSubmission = useEventsStore((s) => s.addSubmission);

  const [teamName, setTeamName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [pptFile, setPptFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [rubricText, setRubricText] = useState(DEFAULT_RUBRIC_TEXT);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!teamName.trim() || !repoUrl.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const presentationRubric = Object.values(
        event?.criteriaConfig?.criteria || {}
      )
        .filter(
          (c: any) =>
            c.artifactId === "presentation" && c.selected
        )
        .map((c: any) => ({
          category: c.label,
          description: c.description,
          max_score: c.weight,
        }));

      if (pptFile && presentationRubric.length === 0) {
        throw new Error(
          "No presentation rubric found for this event. Please ask the organizer to add presentation criteria."
        );
      }

      const { submission: workerSubmission, run } = await submitWorkerProject({
        teamName: teamName.trim(),
        repoUrl: repoUrl.trim(),
        branch: branch.trim() || undefined,
        pptFile,
        rubricCriteria: presentationRubric,
        videoFile,
        rubricCriteria,
        eventId,
      });

      const submission: Submission = {
        id: workerSubmission.id,
        eventId,
        teamName: teamName.trim(),
        repoUrl: repoUrl.trim(),
        branch: branch.trim() || undefined,
        runId: workerSubmission.analysis_job_id,
        run,
        workerSubmissionId: workerSubmission.id,
        analysisJobId: workerSubmission.analysis_job_id,
        pptFileName: pptFile?.name,
        videoFileName: videoFile?.name,
        videoAnalysisStatus: "idle",
        videoAnalysisResult: null,
        voiceStatus: "idle",
        voiceTranscript: null,
        createdAt: new Date().toISOString(),
      };

      addSubmission(eventId, submission);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 py-16">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-md w-full rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center space-y-4"
        >
          <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />

          <h1 className="text-xl font-semibold text-white">
            Submission received
          </h1>

          <p className="text-sm text-neutral-400 leading-relaxed">
            Your repository analysis has started. If you uploaded a presentation,
            it will be evaluated using the organizer&apos;s rubric.
          </p>

          <Link
            href="/"
            className="inline-block rounded-xl bg-neutral-800 px-5 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors"
          >
            Done
          </Link>
        </motion.div>
      </div>
    );
  }

  const title = event?.name ?? "Team submission";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-neutral-800 px-4 py-4 sm:px-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Home
        </Link>
      </header>

      <div className="mx-auto max-w-md px-4 py-10 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-400 mb-2">
            Submit your work
          </p>

          <h1 className="text-2xl font-semibold text-white tracking-tight">
            {title}
          </h1>

          {!event && (
            <p className="mt-2 text-sm text-neutral-500">
              Paste the link your organizer shared. Your submission will be
              attached to this event.
            </p>
          )}

          {event && (
            <p className="mt-2 text-sm text-neutral-500">
              Presentation submissions will automatically use the organizer&apos;s
              dynamic rubric.
            </p>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                Team name <span className="text-violet-400">*</span>
              </label>

              <input
                type="text"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="e.g. Team Alpha"
                className={cn(
                  "w-full h-12 rounded-lg border border-neutral-700 bg-neutral-900 px-3.5 text-base text-white placeholder:text-neutral-600",
                  "focus:outline-none focus:border-violet-500"
                )}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                GitHub repository URL <span className="text-violet-400">*</span>
              </label>

              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
                className={cn(
                  "w-full h-12 rounded-lg border border-neutral-700 bg-neutral-900 px-3.5 text-base text-white placeholder:text-neutral-600",
                  "focus:outline-none focus:border-violet-500"
                )}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                Branch{" "}
                <span className="text-neutral-500 font-normal">
                  (optional)
                </span>
              </label>

              <div className="relative">
                <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />

                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className={cn(
                    "w-full h-12 rounded-lg border border-neutral-700 bg-neutral-900 pl-10 pr-3.5 text-base text-white placeholder:text-neutral-600",
                    "focus:outline-none focus:border-violet-500"
                  )}
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                Presentation{" "}
                <span className="text-neutral-500 font-normal">
                  (optional)
                </span>
              </label>

              <input
                type="file"
                accept=".pptx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                onChange={(event) =>
                  setPptFile(event.target.files?.[0] ?? null)
                }
                className={cn(
                  "w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3.5 py-2 text-sm text-neutral-300",
                  "file:mr-3 file:rounded-md file:border-0 file:bg-neutral-800 file:px-2.5 file:py-1 file:text-xs file:text-neutral-200",
                  "focus:outline-none focus:border-violet-500"
                )}
                disabled={isSubmitting}
              />

              <p className="text-xs text-neutral-500">
                PPT/PDF analysis will use the professor-defined presentation
                rubric automatically.
              </p>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                Demo video <span className="text-neutral-500 font-normal">(optional)</span>
              </label>
              <input
                type="file"
                accept=".mp4,.webm,.mov,.mkv,video/*"
                onChange={(event) => setVideoFile(event.target.files?.[0] ?? null)}
                className={cn(
                  "w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3.5 py-2 text-sm text-neutral-300",
                  "file:mr-3 file:rounded-md file:border-0 file:bg-neutral-800 file:px-2.5 file:py-1 file:text-xs file:text-neutral-200",
                  "focus:outline-none focus:border-violet-500",
                )}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-neutral-300">
                Rubric JSON
              </label>
              <textarea
                value={rubricText}
                onChange={(event) => setRubricText(event.target.value)}
                rows={7}
                className={cn(
                  "w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3.5 py-2 font-mono text-xs text-neutral-200 placeholder:text-neutral-600",
                  "focus:outline-none focus:border-violet-500",
                )}
                disabled={isSubmitting}
              />
            </div>

            {error && (
              <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={!teamName.trim() || !repoUrl.trim() || isSubmitting}
              className={cn(
                "w-full h-12 rounded-xl text-base font-semibold transition-all",
                "bg-violet-600 text-white hover:bg-violet-500",
                "disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              )}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Submitting…
                </>
              ) : (
                "Submit project"
              )}
            </button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}