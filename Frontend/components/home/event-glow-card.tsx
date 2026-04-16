"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Trophy, GraduationCap, Layers, ArrowRight, Users, Calendar } from "lucide-react";
import { GlowCard } from "@/components/ui/spotlight-card";
import { cn } from "@/lib/utils";
import type { EvalEvent } from "@/lib/types";

const TYPE_CONFIG = {
  hackathon: {
    icon: Trophy,
    label: "Hackathon",
    color: "text-warning",
    bg: "bg-warning/10",
    glow: "orange" as const,
  },
  course: {
    icon: GraduationCap,
    label: "Course Evaluation",
    color: "text-violet",
    bg: "bg-violet/10",
    glow: "purple" as const,
  },
  custom: {
    icon: Layers,
    label: "Custom",
    color: "text-success",
    bg: "bg-success/10",
    glow: "green" as const,
  },
};

const STATUS_CONFIG = {
  active: { label: "Active", dot: "bg-success", text: "text-success" },
  draft: { label: "Draft", dot: "bg-warning", text: "text-warning" },
  completed: { label: "Completed", dot: "bg-muted-foreground", text: "text-muted-foreground" },
};

interface EventGlowCardProps {
  event: EvalEvent;
  index: number;
}

export function EventGlowCard({ event, index }: EventGlowCardProps) {
  const typeConf = TYPE_CONFIG[event.type];
  const statusConf = STATUS_CONFIG[event.status];
  const TypeIcon = typeConf.icon;

  const deadline = new Date(event.judgingDeadline).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <Link href={`/events/${event.id}`}>
        <GlowCard glowColor={typeConf.glow} customSize className="!rounded-[14px] group cursor-pointer p-4 sm:p-5">
          {/* Top row: type badge + status */}
          <div className="flex items-center justify-between">
            <div className={cn("flex items-center gap-2 rounded-lg px-2.5 py-1.5", typeConf.bg)}>
              <TypeIcon className={cn("h-3.5 w-3.5", typeConf.color)} />
              <span className={cn("text-[11px] font-semibold tracking-wide", typeConf.color)}>
                {typeConf.label}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", statusConf.dot)} />
              <span className={cn("text-[11px] font-medium", statusConf.text)}>
                {statusConf.label}
              </span>
            </div>
          </div>

          {/* Event name */}
          <div className="mt-4">
            <h2 className="text-base sm:text-[17px] font-semibold leading-snug tracking-tight text-foreground">
              {event.name}
            </h2>
          </div>

          {/* Meta row */}
          <div className="mt-3 flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-[12px] text-muted-foreground">
              <Users className="h-3.5 w-3.5" />
              <span>{event.teamsTotal} teams</span>
            </div>
            <div className="flex items-center gap-1.5 text-[12px] text-muted-foreground">
              <Calendar className="h-3.5 w-3.5" />
              <span>{deadline}</span>
            </div>
          </div>

          {/* Open arrow */}
          <div className="mt-4 flex items-center justify-end">
            <span className="flex items-center gap-1 text-[12px] font-medium text-muted-foreground transition-colors group-hover:text-foreground">
              {event.status === "draft" ? "Continue setup" : "Open"}
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          </div>
        </GlowCard>
      </Link>
    </motion.div>
  );
}
