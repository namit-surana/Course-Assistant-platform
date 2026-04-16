"use client";

import { motion } from "framer-motion";
import {
  Sparkles,
  Upload,
  UserCheck,
  CalendarPlus,
  Send,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MOCK_ACTIVITY } from "@/lib/mock-data";
import type { ActivityItem } from "@/lib/types";

const ACTIVITY_CONFIG: Record<
  ActivityItem["type"],
  { icon: React.ElementType; color: string; bg: string }
> = {
  analysis_complete: { icon: Sparkles, color: "text-violet", bg: "bg-violet/10" },
  submission: { icon: Upload, color: "text-success", bg: "bg-success/10" },
  judge_action: { icon: UserCheck, color: "text-warning", bg: "bg-warning/10" },
  event_created: { icon: CalendarPlus, color: "text-muted-foreground", bg: "bg-muted/50" },
  result_published: { icon: Send, color: "text-success", bg: "bg-success/10" },
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const row = {
  hidden: { opacity: 0, x: -8 },
  show: { opacity: 1, x: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

export function ActivityFeed() {
  return (
    <div className="glass rounded-xl p-4">
      <h2 className="mb-4 text-[13px] font-semibold uppercase tracking-widest text-muted-foreground">
        Recent Activity
      </h2>

      <motion.ul
        variants={container}
        initial="hidden"
        animate="show"
        className="flex flex-col gap-1"
      >
        {MOCK_ACTIVITY.map((item, i) => {
          const conf = ACTIVITY_CONFIG[item.type];
          const Icon = conf.icon;

          return (
            <motion.li
              key={item.id}
              variants={row}
              className={cn(
                "flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-accent/40",
                i < MOCK_ACTIVITY.length - 1 && "border-b border-border/50",
              )}
            >
              <div className={cn("mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg", conf.bg)}>
                <Icon className={cn("h-3.5 w-3.5", conf.color)} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] text-foreground">{item.description}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{item.meta}</p>
              </div>
              <span className="flex-shrink-0 text-[11px] tabular-nums text-muted-foreground">
                {item.time}
              </span>
            </motion.li>
          );
        })}
      </motion.ul>
    </div>
  );
}
