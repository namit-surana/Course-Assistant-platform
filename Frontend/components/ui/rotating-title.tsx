"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

interface RotatingTitleProps {
  words: string[];
  intervalMs?: number;
  className?: string;
}

export function RotatingTitle({
  words,
  intervalMs = 2200,
  className = "",
}: RotatingTitleProps) {
  const [titleNumber, setTitleNumber] = useState(0);
  const titles = useMemo(() => words.filter(Boolean), [words]);

  useEffect(() => {
    if (titles.length <= 1) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setTitleNumber((current) => (current === titles.length - 1 ? 0 : current + 1));
    }, intervalMs);

    return () => window.clearTimeout(timeoutId);
  }, [intervalMs, titleNumber, titles]);

  if (titles.length === 0) {
    return null;
  }

  return (
    <span className={`relative flex min-h-[1.15em] items-center overflow-hidden ${className}`}>
      {titles.map((title, index) => (
        <motion.span
          key={title}
          className="absolute font-semibold"
          initial={{ opacity: 0, y: -80 }}
          animate={
            titleNumber === index
              ? { opacity: 1, y: 0 }
              : { opacity: 0, y: titleNumber > index ? -120 : 120 }
          }
          transition={{ type: "spring", stiffness: 55, damping: 15 }}
        >
          {title}
        </motion.span>
      ))}
    </span>
  );
}
