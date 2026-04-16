"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, GitBranch, Loader2 } from "lucide-react";
import { useEventsStore } from "@/lib/events-store";
import type { AnalysisRunState, Submission } from "@/lib/types";
import { cn } from "@/lib/utils";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

interface Props {
  eventId: string;
  open: boolean;
  onClose: () => void;
}

export function AddSubmissionModal({ eventId, open, onClose }: Props) {
  const addSubmission = useEventsStore((s) => s.addSubmission);
  const [teamName, setTeamName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTeamName("");
    setRepoUrl("");
    setBranch("");
    setError(null);
    setIsSubmitting(false);
  }

  function handleClose() {
    if (isSubmitting) return;
    reset();
    onClose();
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!teamName.trim() || !repoUrl.trim()) return;
    setError(null);
    setIsSubmitting(true);

    try {
      const payload: { repo_url: string; branch?: string } = {
        repo_url: repoUrl.trim(),
      };
      if (branch.trim()) payload.branch = branch.trim();

      const resp = await fetch(`${API_BASE_URL}/api/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const failure = await resp.json().catch(() => ({}));
        throw new Error(failure.detail || "Failed to start analysis.");
      }

      const run = (await resp.json()) as AnalysisRunState;

      const submission: Submission = {
        id: `sub-${Date.now()}`,
        eventId,
        teamName: teamName.trim(),
        repoUrl: repoUrl.trim(),
        branch: branch.trim() || undefined,
        runId: run.id,
        run,
        createdAt: new Date().toISOString(),
      };

      addSubmission(eventId, submission);
      reset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = teamName.trim().length > 0 && repoUrl.trim().length > 0 && !isSubmitting;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-950 shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
                <div>
                  <h2 className="text-base font-semibold text-white">Add Team Submission</h2>
                  <p className="text-xs text-neutral-400 mt-0.5">
                    Enter the GitHub repo to start AI analysis
                  </p>
                </div>
                <button
                  onClick={handleClose}
                  className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
                {/* Team Name */}
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-neutral-300">
                    Team Name <span className="text-violet-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={teamName}
                    onChange={(e) => setTeamName(e.target.value)}
                    placeholder="e.g. Team Nexus"
                    className={cn(
                      "w-full h-11 rounded-lg border border-neutral-700 bg-neutral-900",
                      "px-3.5 text-sm text-white placeholder:text-neutral-600",
                      "focus:outline-none focus:border-violet-500 transition-colors"
                    )}
                    disabled={isSubmitting}
                  />
                </div>

                {/* GitHub URL */}
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-neutral-300">
                    GitHub Repository URL <span className="text-violet-400">*</span>
                  </label>
                  <input
                    type="url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/owner/repo"
                    className={cn(
                      "w-full h-11 rounded-lg border border-neutral-700 bg-neutral-900",
                      "px-3.5 text-sm text-white placeholder:text-neutral-600",
                      "focus:outline-none focus:border-violet-500 transition-colors"
                    )}
                    disabled={isSubmitting}
                  />
                </div>

                {/* Branch */}
                <div className="space-y-1.5">
                  <label className="text-sm font-semibold text-neutral-300">
                    Branch{" "}
                    <span className="text-neutral-500 font-normal">(optional, default: main)</span>
                  </label>
                  <div className="relative">
                    <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                    <input
                      type="text"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      placeholder="main"
                      className={cn(
                        "w-full h-11 rounded-lg border border-neutral-700 bg-neutral-900",
                        "pl-9 pr-3.5 text-sm text-white placeholder:text-neutral-600",
                        "focus:outline-none focus:border-violet-500 transition-colors"
                      )}
                      disabled={isSubmitting}
                    />
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                    {error}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center gap-3 pt-1">
                  <button
                    type="button"
                    onClick={handleClose}
                    disabled={isSubmitting}
                    className="flex-1 h-10 rounded-lg border border-neutral-700 text-sm font-medium text-neutral-300 hover:bg-neutral-800 transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit}
                    className={cn(
                      "flex-1 h-10 rounded-lg text-sm font-semibold transition-all",
                      "bg-violet-600 text-white hover:bg-violet-500",
                      "disabled:opacity-40 disabled:cursor-not-allowed",
                      "flex items-center justify-center gap-2"
                    )}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Starting…
                      </>
                    ) : (
                      "Start Analysis →"
                    )}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
