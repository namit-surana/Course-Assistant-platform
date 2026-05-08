"use client";

import { useEffect, useMemo, useState } from "react";

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
    if (titles.length <= 1) return;

    const timer = window.setInterval(() => {
      setTitleNumber((current) => (current + 1) % titles.length);
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [intervalMs, titles.length]);

  if (titles.length === 0) {
    return null;
  }

  return (
    <span className={`inline-flex min-h-[1.15em] items-center ${className}`}>
      <span key={`${titles[titleNumber]}-${titleNumber}`} className="font-semibold">
        {titles[titleNumber]}
      </span>
    </span>
  );
}
