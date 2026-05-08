"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Trophy,
  GraduationCap,
  Layers,
  Users,
  Inbox,
  Trash2,
  Share2,
  Copy,
  GitBranch,
  FileText,
  ChevronRight,
  CheckCircle2,
  Clock3,
  Loader2,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useEventsStore } from "@/lib/events-store";
import { AddSubmissionModal } from "./add-submission-modal";
import type { Submission } from "@/lib/types";

const TYPE_CONFIG = {
  hackathon: {
    icon: Trophy,
    label: "Hackathon",
    color: "text-warning",
    bg: "bg-warning/10",
  },
  course: {
    icon: GraduationCap,
    label: "Course",
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  custom: {
    icon: Layers,
    label: "Custom",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
};

const STATUS_CONFIG = {
  active: {
    label: "Active",
    dot: "bg-emerald-400",
    text: "text-emerald-400",
  },
  draft: {
    label: "Draft",
    dot: "bg-amber-400",
    text: "text-amber-400",
  },
  completed: {
    label: "Completed",
    dot: "bg-neutral-400",
    text: "text-neutral-400",
  },
};

const EMPTY_SUBMISSIONS: Submission[] = [];

export function EventDetailPage({ eventId }: { eventId: string }) {
  const router = useRouter();

  const event = useEventsStore((s) =>
    s.events.find((e) => e.id === eventId)
  );
  const submissions = useEventsStore(
    (s) => s.submissions[eventId] ?? EMPTY_SUBMISSIONS
  );
  const isLoadingEvents = useEventsStore((s) => s.isLoadingEvents);
  const loadEvents = useEventsStore((s) => s.loadEvents);
  const loadSubmissions = useEventsStore((s) => s.loadSubmissions);
  const deleteEvent = useEventsStore((s) => s.deleteEvent);

  const [modalOpen, setModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    void loadEvents();
    void loadSubmissions(eventId);
  }, [eventId, loadEvents, loadSubmissions]);

  if (!event) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-neutral-400">
          {isLoadingEvents ? "Loading event..." : "Event not found."}
        </p>
      </div>
    );
  }

  const typeConf = TYPE_CONFIG[event.type];
  const statusConf = STATUS_CONFIG[event.status];
  const TypeIcon = typeConf.icon;

  const total = submissions.length;
  const analyzed = submissions.filter(
    (s) => s.run.status === "completed"
  ).length;
  const running = submissions.filter(
    (s) => s.run.status === "running" || s.run.status === "queued"
  ).length;
  const failed = submissions.filter((s) => s.run.status === "failed").length;

  function openSubmission(sub: Submission) {
    router.push(`/events/${eventId}/submissions/${sub.id}?demo=1`);
  }

  async function handleDeleteEvent() {
    const ok = window.confirm(
      "Are you sure you want to delete this event? This action cannot be undone."
    );

    if (!ok) return;

    setIsDeleting(true);

    try {
      await deleteEvent(eventId);
      router.push("/home");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete event.");
      setIsDeleting(false);
    }
  }

  async function handleShare() {
    const url = event?.studentSubmitUrl;
    if (!url) {
      alert("No student submission link is available for this event.");
      return;
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // Fallback: open in a new tab so the user can copy manually.
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <motion.nav
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="sticky top-0 z-30 flex items-center gap-3 border-b border-neutral-800/60 bg-background/80 px-4 py-3 backdrop-blur-md sm:px-6"
      >
        <button
          onClick={() => router.back()}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-neutral-800 text-neutral-400 hover:bg-neutral-800 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-md px-2 py-1 shrink-0",
              typeConf.bg
            )}
          >
            <TypeIcon className={cn("h-3.5 w-3.5", typeConf.color)} />
            <span className={cn("text-[11px] font-semibold", typeConf.color)}>
              {typeConf.label}
            </span>
          </div>

          <h1 className="truncate text-sm font-semibold text-white sm:text-base">
            {event.name}
          </h1>

          <div className="hidden items-center gap-1.5 sm:flex shrink-0">
            <span className={cn("h-1.5 w-1.5 rounded-full", statusConf.dot)} />
            <span className={cn("text-xs font-medium", statusConf.text)}>
              {statusConf.label}
            </span>
          </div>
        </div>

        <button
          onClick={handleDeleteEvent}
          disabled={isDeleting}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Trash2 className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">
            {isDeleting ? "Deleting..." : "Delete"}
          </span>
        </button>

        <button
          onClick={() => void handleShare()}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-neutral-800 px-3 py-1.5 text-xs font-semibold text-neutral-200 hover:bg-neutral-800 transition-colors sm:px-4 sm:text-sm"
          title={event.studentSubmitUrl ? "Copy student submission link" : "No submit link available"}
        >
          {copied ? <Copy className="h-3.5 w-3.5" /> : <Share2 className="h-3.5 w-3.5" />}
          <span className="hidden sm:inline">{copied ? "Copied" : "Share"}</span>
          <span className="sm:hidden">{copied ? "Copied" : "Share"}</span>
        </button>

        <button
          onClick={() => setModalOpen(true)}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition-colors sm:px-4 sm:text-sm"
        >
          <Plus className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Add Team</span>
          <span className="sm:hidden">Add</span>
        </button>
      </motion.nav>

      <div className="w-full px-4 py-6 sm:px-8">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2"
        >
          <StatItem icon={<Users className="h-3.5 w-3.5" />} label="Total" value={total} />
          <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
          <StatItem label="Analyzed" value={analyzed} color="text-emerald-400" />
          <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
          <StatItem label="In Progress" value={running} color="text-violet-400" />

          {failed > 0 && (
            <>
              <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
              <StatItem label="Failed" value={failed} color="text-red-400" />
            </>
          )}
        </motion.div>

        {submissions.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-neutral-800 py-20 text-center"
          >
            <Inbox className="mb-3 h-8 w-8 text-neutral-600" />
            <p className="text-sm font-medium text-neutral-400">
              No submissions yet
            </p>
            <p className="mt-1 text-xs text-neutral-600">
              Click Add Team to submit a GitHub repo for AI analysis
            </p>

            <button
              onClick={() => setModalOpen(true)}
              className="mt-5 flex items-center gap-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 px-4 py-2 text-sm font-medium text-violet-300 hover:bg-violet-600/30 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add First Team
            </button>
          </motion.div>
        ) : (
          <div className="max-w-full overflow-x-auto rounded-xl border border-neutral-800 bg-neutral-900/40">
            <table className="w-full min-w-[940px] table-fixed border-collapse">
              <colgroup>
                <col style={{ width: "34%" }} />
                <col style={{ width: "18%" }} />
                <col style={{ width: "20%" }} />
                <col style={{ width: "14%" }} />
                <col style={{ width: "14%" }} />
              </colgroup>
              <thead>
                <tr className="border-b border-neutral-800 bg-neutral-900/80">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Team
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Artifacts
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Pipeline Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Final Score
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-neutral-400">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub, i) => (
                  <motion.tr
                    key={sub.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className={cn(
                      "border-b border-neutral-800/70 last:border-b-0 hover:bg-neutral-800/40 cursor-pointer transition-colors",
                      i % 2 === 0 ? "bg-neutral-900/20" : "bg-neutral-900/40"
                    )}
                    onClick={() => openSubmission(sub)}
                  >
                    <td className="px-4 py-3.5">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-white">
                          {sub.teamName}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-neutral-500">
                          {sub.repoUrl ? shortRepo(sub.repoUrl) : "No repository URL"}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <ArtifactsPills submission={sub} />
                    </td>
                    <td className="px-4 py-3.5">
                      <PipelineStatusPill status={sub.run.status} />
                    </td>
                    <td className="px-4 py-3.5">
                      {sub.finalOverallScore !== undefined && sub.finalOverallMaxScore !== undefined ? (
                        <span className="text-sm font-semibold text-emerald-300">
                          {sub.finalOverallScore}/{sub.finalOverallMaxScore}
                        </span>
                      ) : (
                        <span className="text-sm text-neutral-500">Pending</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openSubmission(sub);
                        }}
                        className="inline-flex items-center gap-1.5 rounded-md border border-neutral-700 px-3 py-1.5 text-xs font-medium text-neutral-200 hover:border-violet-500/60 hover:text-white"
                      >
                        View
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AddSubmissionModal
        eventId={eventId}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}

function shortRepo(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
}

function YouTubeGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.6 3.5 12 3.5 12 3.5s-7.6 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.8.6 9.4.6 9.4.6s7.6 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.8 15.6V8.4l6.2 3.6-6.2 3.6Z" />
    </svg>
  );
}

function ArtifactsPills({ submission }: { submission: Submission }) {
  const hasRepo = Boolean(submission.repoUrl?.trim());
  const hasPpt = Boolean(submission.pptFileName);
  const hasVideo = Boolean(submission.videoFileName || submission.videoObjectKey);

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn("inline-flex items-center rounded-md border px-1.5 py-1", hasRepo ? "border-neutral-600 text-neutral-200" : "border-neutral-800 text-neutral-700")}
        title={hasRepo ? "Repository uploaded" : "Repository missing"}
      >
        <GitBranch className="h-3.5 w-3.5" />
      </span>
      <span
        className={cn("inline-flex items-center rounded-md border px-1.5 py-1", hasPpt ? "border-neutral-600 text-neutral-200" : "border-neutral-800 text-neutral-700")}
        title={hasPpt ? "Presentation uploaded" : "Presentation missing"}
      >
        <FileText className="h-3.5 w-3.5" />
      </span>
      <span
        className={cn("inline-flex items-center rounded-md border px-1.5 py-1", hasVideo ? "border-red-500/40 text-red-400" : "border-neutral-800 text-neutral-700")}
        title={hasVideo ? "Demo video uploaded" : "Demo video missing"}
      >
        <YouTubeGlyph className="h-3.5 w-3.5" />
      </span>
    </div>
  );
}

function PipelineStatusPill({ status }: { status: Submission["run"]["status"] }) {
  if (status === "completed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300">
        <CheckCircle2 className="h-3 w-3" /> Completed
      </span>
    );
  }
  if (status === "running" || status === "queued") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/15 px-2.5 py-1 text-xs font-medium text-violet-300">
        <Loader2 className="h-3 w-3 animate-spin" /> Analyzing
      </span>
    );
  }
  if (status === "submitted") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-neutral-800 px-2.5 py-1 text-xs font-medium text-neutral-400">
        <Clock3 className="h-3 w-3" /> Submitted
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2.5 py-1 text-xs font-medium text-red-300">
      <XCircle className="h-3 w-3" /> Failed
    </span>
  );
}

function StatItem({
  icon,
  label,
  value,
  color = "text-white",
}: {
  icon?: React.ReactNode;
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 text-sm">
      {icon && <span className="text-neutral-500">{icon}</span>}
      <span className={cn("font-semibold", color)}>{value}</span>
      <span className="text-neutral-500">{label}</span>
    </div>
  );
}