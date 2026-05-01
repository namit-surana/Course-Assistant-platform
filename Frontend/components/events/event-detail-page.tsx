"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, Trophy, GraduationCap, Layers, Users, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEventsStore } from "@/lib/events-store";
import { SubmissionCard } from "./submission-card";
import { AddSubmissionModal } from "./add-submission-modal";
import { SubmissionDetailPanel } from "./submission-detail-panel";
import type { Submission } from "@/lib/types";

const TYPE_CONFIG = {
  hackathon: { icon: Trophy,        label: "Hackathon", color: "text-warning",     bg: "bg-warning/10" },
  course:    { icon: GraduationCap, label: "Course",    color: "text-violet-400",  bg: "bg-violet-500/10" },
  custom:    { icon: Layers,        label: "Custom",    color: "text-emerald-400", bg: "bg-emerald-500/10" },
};

const STATUS_CONFIG = {
  active:    { label: "Active",    dot: "bg-emerald-400", text: "text-emerald-400" },
  draft:     { label: "Draft",     dot: "bg-amber-400",   text: "text-amber-400" },
  completed: { label: "Completed", dot: "bg-neutral-400", text: "text-neutral-400" },
};

const EMPTY_SUBMISSIONS: Submission[] = [];

export function EventDetailPage({ eventId }: { eventId: string }) {
  const router      = useRouter();
  const event       = useEventsStore((s) => s.events.find((e) => e.id === eventId));
  const submissions = useEventsStore((s) => s.submissions[eventId] ?? EMPTY_SUBMISSIONS);
  const [modalOpen,  setModalOpen]  = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (!event) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-neutral-400">Event not found.</p>
      </div>
    );
  }

  const typeConf   = TYPE_CONFIG[event.type];
  const statusConf = STATUS_CONFIG[event.status];
  const TypeIcon   = typeConf.icon;

  const total    = submissions.length;
  const analyzed = submissions.filter((s) => s.run.status === "completed").length;
  const running  = submissions.filter((s) => s.run.status === "running" || s.run.status === "queued").length;
  const failed   = submissions.filter((s) => s.run.status === "failed").length;

  const selectedSub = submissions.find((s) => s.id === selectedId) ?? null;
  const panelOpen   = selectedSub !== null;

  function handleSelectCard(sub: Submission) {
    setSelectedId((prev) => (prev === sub.id ? null : sub.id));
  }

  return (
    <div className="min-h-screen bg-background">

      {/* ── Sticky top nav ─────────────────────────────────────────────── */}
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
          <div className={cn("flex items-center gap-1.5 rounded-md px-2 py-1 shrink-0", typeConf.bg)}>
            <TypeIcon className={cn("h-3.5 w-3.5", typeConf.color)} />
            <span className={cn("text-[11px] font-semibold", typeConf.color)}>{typeConf.label}</span>
          </div>
          <h1 className="truncate text-sm font-semibold text-white sm:text-base">{event.name}</h1>
          <div className="hidden items-center gap-1.5 sm:flex shrink-0">
            <span className={cn("h-1.5 w-1.5 rounded-full", statusConf.dot)} />
            <span className={cn("text-xs font-medium", statusConf.text)}>{statusConf.label}</span>
          </div>
        </div>

        <button
          onClick={() => setModalOpen(true)}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 transition-colors sm:px-4 sm:text-sm"
        >
          <Plus className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Add Team</span>
          <span className="sm:hidden">Add</span>
        </button>
      </motion.nav>

      {/* ── Page content ───────────────────────────────────────────────── */}
      <div className="px-4 py-6 sm:px-8 max-w-xl">

        {/* Stats bar */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-5 flex flex-wrap items-center gap-x-6 gap-y-2"
        >
          <StatItem icon={<Users className="h-3.5 w-3.5" />} label="Total"       value={total} />
          <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
          <StatItem label="Analyzed"    value={analyzed} color="text-emerald-400" />
          <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
          <StatItem label="In Progress" value={running}  color="text-violet-400" />
          {failed > 0 && (
            <>
              <div className="h-4 w-px bg-neutral-800 hidden sm:block" />
              <StatItem label="Failed" value={failed} color="text-red-400" />
            </>
          )}
        </motion.div>

        {/* Submission list */}
        {submissions.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-neutral-800 py-20 text-center"
          >
            <Inbox className="mb-3 h-8 w-8 text-neutral-600" />
            <p className="text-sm font-medium text-neutral-400">No submissions yet</p>
            <p className="mt-1 text-xs text-neutral-600">
              Click "Add Team" to submit a GitHub repo for AI analysis
            </p>
            <button
              onClick={() => setModalOpen(true)}
              className="mt-5 flex items-center gap-1.5 rounded-lg bg-violet-600/20 border border-violet-500/30 px-4 py-2 text-sm font-medium text-violet-300 hover:bg-violet-600/30 transition-colors"
            >
              <Plus className="h-4 w-4" /> Add First Team
            </button>
          </motion.div>
        ) : (
          <div className="space-y-2">
            {submissions.map((sub, i) => (
              <motion.div
                key={sub.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <SubmissionCard
                  submission={sub}
                  eventId={eventId}
                  isSelected={selectedId === sub.id}
                  onClick={() => handleSelectCard(sub)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* ── Overlay panel ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {panelOpen && (
          <>
            {/* Dim backdrop — click to close */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[2px]"
              onClick={() => setSelectedId(null)}
            />

            {/* Sliding panel */}
            <motion.div
              key="panel"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: 0.28, ease: [0.25, 0.46, 0.45, 0.94] }}
              className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-[620px] border-l border-neutral-800 bg-neutral-950 shadow-2xl"
            >
              {selectedSub && (
                <SubmissionDetailPanel
                  eventId={eventId}
                  submission={selectedSub}
                  onClose={() => setSelectedId(null)}
                />
              )}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Modal ──────────────────────────────────────────────────────── */}
      <AddSubmissionModal
        eventId={eventId}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}

function StatItem({
  icon, label, value, color = "text-white",
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
