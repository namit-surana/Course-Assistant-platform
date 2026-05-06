"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { submitWorkerProject } from "@/lib/backend-submissions";
import { useEventsStore } from "@/lib/events-store";
import { presentationRubricFromCriteriaConfig } from "@/lib/presentation-rubric";
import type { Submission } from "@/lib/types";

interface Props {
  eventId: string;
  open: boolean;
  onClose: () => void;
}

export function AddSubmissionModal({ eventId, open, onClose }: Props) {
  const event = useEventsStore((s) =>
    s.events.find((e) => e.id === eventId)
  );
  const addSubmission = useEventsStore((s) => s.addSubmission);

  const [teamName, setTeamName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [pptFile, setPptFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTeamName("");
    setRepoUrl("");
    setBranch("");
    setPptFile(null);
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
      const presentationRubric = presentationRubricFromCriteriaConfig(
        event?.criteriaConfig as Record<string, unknown> | undefined
      );

      if (pptFile && presentationRubric.length === 0) {
        throw new Error(
          "No valid presentation rubric found. Ask organizer to configure criteria."
        );
      }

      const { submission: workerSubmission, run } =
        await submitWorkerProject({
          teamName: teamName.trim(),
          repoUrl: repoUrl.trim(),
          branch: branch.trim() || undefined,
          pptFile,
          rubricCriteria: presentationRubric,
          eventId,
        });

      const submission: Submission = {
        id: workerSubmission.id,
        eventId,
        teamName: teamName.trim(),
        repoUrl: repoUrl.trim(),
        branch: branch.trim() || undefined,
        run,
        workerSubmissionId: workerSubmission.id,
        pptFileName: pptFile?.name,
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

  const canSubmit =
    teamName.trim().length > 0 &&
    repoUrl.trim().length > 0 &&
    !isSubmitting;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={handleClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div className="w-full max-w-md rounded-2xl backdrop-blur-xl bg-neutral-950/80 border border-neutral-800 shadow-2xl">

              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800">
                <div>
                  <h2 className="text-lg font-semibold text-white">
                    Add Submission
                  </h2>
                  <p className="text-xs text-neutral-400">
                    Submit your project for AI evaluation
                  </p>
                </div>

                <button onClick={handleClose}>
                  <X className="h-4 w-4 text-neutral-400 hover:text-white" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="px-6 py-6 space-y-5">

                {/* Team */}
                <input
                  type="text"
                  placeholder="Team Name"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  className="w-full h-11 rounded-xl bg-neutral-900 border border-neutral-700 px-4 text-white placeholder:text-neutral-500 focus:ring-2 focus:ring-violet-500 outline-none"
                />

                {/* Repo */}
                <input
                  type="url"
                  placeholder="GitHub Repository URL"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="w-full h-11 rounded-xl bg-neutral-900 border border-neutral-700 px-4 text-white placeholder:text-neutral-500 focus:ring-2 focus:ring-violet-500 outline-none"
                />

                {/* Branch */}
                <input
                  type="text"
                  placeholder="Branch (optional)"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full h-11 rounded-xl bg-neutral-900 border border-neutral-700 px-4 text-white placeholder:text-neutral-500 focus:ring-2 focus:ring-violet-500 outline-none"
                />

                {/* Upload */}
                <div className="space-y-2">
                  <label className="text-sm text-neutral-300">
                    Upload Presentation (optional)
                  </label>

                  <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-neutral-700 rounded-xl cursor-pointer hover:border-violet-500 transition">
                    <span className="text-xs text-neutral-400">
                      Click to upload PPT / PDF
                    </span>
                    <input
                      type="file"
                      accept=".pptx,.pdf"
                      className="hidden"
                      onChange={(e) =>
                        setPptFile(e.target.files?.[0] || null)
                      }
                    />
                  </label>

                  {pptFile && (
                    <p className="text-xs text-neutral-400">
                      {pptFile.name}
                    </p>
                  )}
                </div>

                {/* Error */}
                {error && (
                  <div className="text-sm text-red-400 bg-red-500/10 px-3 py-2 rounded-lg border border-red-500/20">
                    {error}
                  </div>
                )}

                {/* Button */}
                <button
                  type="submit"
                  disabled={!canSubmit}
                  className="w-full h-11 rounded-xl font-semibold text-white bg-gradient-to-r from-violet-600 to-purple-500 hover:from-violet-500 hover:to-purple-400 transition disabled:opacity-40 flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    "🚀 Submit Project"
                  )}
                </button>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}