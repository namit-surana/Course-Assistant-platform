"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Plus } from "lucide-react";
import { EventGlowCard } from "./event-glow-card";
import { useEventsStore } from "@/lib/events-store";
import { cn } from "@/lib/utils";
import type { EventStatus } from "@/lib/types";

const FILTERS: { label: string; value: EventStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Completed", value: "completed" },
];


export function HomePage() {
  const events  = useEventsStore((s) => s.events);
  const loadEvents = useEventsStore((s) => s.loadEvents);
  const isLoadingEvents = useEventsStore((s) => s.isLoadingEvents);
  const eventsError = useEventsStore((s) => s.eventsError);
  const [filter, setFilter] = useState<EventStatus | "all">("active");

  useEffect(() => {
    void loadEvents();
  }, [loadEvents]);

  const filtered =
    filter === "all" ? events : events.filter((e) => e.status === filter);

  return (
    <div className="min-h-screen bg-background">
      {/* Top nav bar */}
      <motion.nav
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="flex items-center justify-between border-b border-border bg-background/60 px-4 sm:px-8 py-3 backdrop-blur-md sticky top-0 z-10"
      >
        {/* Left: empty — keeps right side aligned */}
        <div />

        {/* Right: New Event + avatar */}
        <div className="flex items-center gap-3">
          <Link
            href="/events/new"
            className="flex items-center gap-2 rounded-xl bg-violet px-4 py-2 text-[13px] font-semibold text-white shadow-lg transition-opacity hover:opacity-90 glow-violet-sm"
          >
            <Plus className="h-3.5 w-3.5" />
            New Event
          </Link>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet/20 ring-2 ring-violet/30 text-xs font-semibold text-violet">
            DC
          </div>
        </div>
      </motion.nav>

      {/* Main content */}
      <div className="mx-auto max-w-5xl px-4 sm:px-8 py-8 sm:py-12">

        {/* Filter tabs */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1, ease: "easeOut" }}
          className="mb-6 flex items-center gap-1 rounded-xl bg-muted/40 p-1 w-fit max-w-full overflow-x-auto"
        >
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={cn(
                "relative rounded-lg px-4 py-1.5 text-[13px] font-medium transition-colors",
                filter === f.value
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {filter === f.value && (
                <motion.div
                  layoutId="home-filter-pill"
                  className="absolute inset-0 rounded-lg bg-card shadow-sm"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative">
                {f.label}
                {f.value !== "all" && (
                  <span className="ml-1.5 text-[11px] text-muted-foreground">
                    {events.filter((e) => e.status === f.value).length}
                  </span>
                )}
              </span>
            </button>
          ))}
        </motion.div>

        {/* Event cards grid */}
        <motion.div
          key={filter}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
          {filtered.map((event, i) => (
            <EventGlowCard key={event.id} event={event} index={i} />
          ))}

          {filtered.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="col-span-full flex flex-col items-center justify-center gap-3 py-20 text-center"
            >
              <p className="text-[15px] text-muted-foreground">
                {isLoadingEvents
                  ? "Loading events..."
                  : eventsError || "No events here yet."}
              </p>
              <Link
                href="/events/new"
                className="text-[13px] font-medium text-violet hover:underline"
              >
                Create your first event →
              </Link>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
