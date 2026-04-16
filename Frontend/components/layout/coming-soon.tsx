"use client";

import { motion } from "framer-motion";
import { Hammer } from "lucide-react";

export function ComingSoon({ title }: { title: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-1 flex-col items-center justify-center gap-4 text-center"
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet/10">
        <Hammer className="h-6 w-6 text-violet" />
      </div>
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground">This screen is coming next.</p>
      </div>
    </motion.div>
  );
}
