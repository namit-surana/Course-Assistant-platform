"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  Trophy,
  GraduationCap,
  Layers,
  ArrowRight,
  MoreHorizontal,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EvalEvent } from "@/lib/types";

const TYPE_CONFIG = {
  hackathon: {
    icon: Trophy,
    label: "Hackathon",
    color: "text-warning",
    bg: "bg-warning/10",
  },
  course: {
    icon: GraduationCap,
    label: "Course Eval",
    color: "text-violet",
    bg: "bg-violet/10",
  },
  custom: {
    icon: Layers,
    label: "Custom",
    color: "text-success",
    bg: "bg-success/10",
  },
};

const STATUS_CONFIG = {
  active: { label: "Active", dot: "bg-success", text: "text-success" },
  draft: { label: "Draft", dot: "bg-warning", text: "text-warning" },
  completed: { label: "Completed", dot: "bg-muted-foreground", text: "text-muted-foreground" },
};

interface EventCardProps {
  event: EvalEvent;
  index: number;
}

export function EventCard({ event, index }: EventCardProps) {
  const typeConf = TYPE_CONFIG[event.type];
  const statusConf = STATUS_CONFIG[event.status];
  const TypeIcon = typeConf.icon;
  const progress = event.teamsTotal > 0
    ? Math.round((event.teamsEvaluated / event.teamsTotal) * 100)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06, ease: "easeOut" }}
      whileHover={{ y: -3, transition: { duration: 0.15 } }}
      className="glass gradient-border group flex flex-col gap-4 rounded-xl p-4"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg", typeConf.bg)}>
            <TypeIcon className={cn("h-4 w-4", typeConf.color)} />
          </div>
          <span className={cn("text-[11px] font-medium", typeConf.color)}>
            {typeConf.label}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", statusConf.dot)} />
            <span className={cn("text-[11px] font-medium", statusConf.text)}>
              {statusConf.label}
            </span>
          </div>
          <button className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-foreground group-hover:opacity-100">
            <MoreHorizontal className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Event name */}
      <div>
        <h3 className="text-[14px] font-semibold tracking-tight text-foreground">
          {event.name}
        </h3>
        <div className="mt-1 flex items-center gap-1 text-[11px] text-muted-foreground">
          <Calendar className="h-3 w-3" />
          <span>Judging closes {new Date(event.judgingDeadline).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
        </div>
      </div>

      {/* Progress */}
      <div>
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-[11px] text-muted-foreground">
            Teams evaluated
          </span>
          <span className="font-mono text-[12px] font-medium text-foreground">
            {event.teamsEvaluated} / {event.teamsTotal}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.8, delay: index * 0.06 + 0.3, ease: "easeOut" }}
            className={cn(
              "h-full rounded-full",
              progress === 100 ? "bg-success" : "bg-violet",
            )}
          />
        </div>
      </div>

      {/* Footer action */}
      <Link
        href={`/events/${event.id}/submissions`}
        className="group/link flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-[12px] font-medium text-muted-foreground transition-colors hover:bg-violet/10 hover:text-violet"
      >
        <span>{event.status === "draft" ? "Continue setup" : "Open workspace"}</span>
        <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover/link:translate-x-0.5" />
      </Link>
    </motion.div>
  );
}
