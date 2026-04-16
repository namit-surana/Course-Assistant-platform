"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { StatCard } from "@/lib/types";

const STATS: StatCard[] = [
  { label: "Active Events", value: 2, sub: "2 in progress", trend: "up" },
  { label: "Teams Evaluated", value: "32/56", sub: "57% complete", trend: "up" },
  { label: "Pending Reviews", value: 8, sub: "Needs attention", trend: "neutral" },
  { label: "Completed Events", value: 2, sub: "All results sent", trend: "neutral" },
];

const TrendIcon = ({ trend }: { trend: StatCard["trend"] }) => {
  if (trend === "up") return <TrendingUp className="h-3.5 w-3.5 text-success" />;
  if (trend === "down") return <TrendingDown className="h-3.5 w-3.5 text-danger" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
};

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07 } },
};

const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
};

export function StatCards() {
  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 gap-3 lg:grid-cols-4"
    >
      {STATS.map((stat) => (
        <motion.div
          key={stat.label}
          variants={item}
          whileHover={{ y: -2, transition: { duration: 0.15 } }}
          className="glass rounded-xl p-4"
        >
          <p className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
            {stat.label}
          </p>
          <div className="mt-2 flex items-end justify-between">
            <span className="font-mono text-2xl font-bold tracking-tight text-foreground">
              {stat.value}
            </span>
            <TrendIcon trend={stat.trend} />
          </div>
          <p className="mt-1 text-[12px] text-muted-foreground">{stat.sub}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}
