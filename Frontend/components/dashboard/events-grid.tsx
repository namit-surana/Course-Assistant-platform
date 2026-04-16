"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Plus } from "lucide-react";
import { EventCard } from "./event-card";
import { MOCK_EVENTS } from "@/lib/mock-data";
import { cn } from "@/lib/utils";
import type { EventStatus } from "@/lib/types";

const FILTERS: { label: string; value: EventStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Completed", value: "completed" },
];

export function EventsGrid() {
  const [filter, setFilter] = useState<EventStatus | "all">("all");

  const filtered = filter === "all"
    ? MOCK_EVENTS
    : MOCK_EVENTS.filter((e) => e.status === filter);

  return (
    <div>
      {/* Section header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-1 rounded-lg bg-muted/40 p-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={cn(
                "relative rounded-md px-3 py-1.5 text-[12px] font-medium transition-colors",
                filter === f.value
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {filter === f.value && (
                <motion.div
                  layoutId="filter-pill"
                  className="absolute inset-0 rounded-md bg-card"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative">{f.label}</span>
            </button>
          ))}
        </div>

        <Link
          href="/events/new"
          className="flex items-center gap-1.5 rounded-lg bg-violet px-3 py-2 text-[12px] font-semibold text-white shadow-sm transition-opacity hover:opacity-90 glow-violet-sm"
        >
          <Plus className="h-3.5 w-3.5" />
          Create Event
        </Link>
      </div>

      {/* Grid */}
      <AnimatePresence mode="popLayout">
        <motion.div
          key={filter}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
        >
          {filtered.map((event, i) => (
            <EventCard key={event.id} event={event} index={i} />
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
