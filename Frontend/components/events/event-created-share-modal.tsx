"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Link2, Copy, Check, PartyPopper } from "lucide-react";
import { cn } from "@/lib/utils";

const APP_ORIGIN =
  typeof process.env.NEXT_PUBLIC_APP_URL === "string" && process.env.NEXT_PUBLIC_APP_URL.length > 0
    ? process.env.NEXT_PUBLIC_APP_URL.replace(/\/$/, "")
    : "";

interface Props {
  open: boolean;
  eventId: string;
  eventName: string;
  onClose: () => void;
}

export function EventCreatedShareModal({ open, eventId, eventName, onClose }: Props) {
  const [shareUrl, setShareUrl] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || !eventId) return;
    const base = APP_ORIGIN || (typeof window !== "undefined" ? window.location.origin : "");
    setShareUrl(`${base}/events/${eventId}/submit`);
  }, [open, eventId]);

  async function copyLink() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] bg-black/65 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.22, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed inset-0 z-[61] flex items-center justify-center p-4"
          >
            <div
              className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-950 shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between gap-3 border-b border-neutral-800 px-5 py-4">
                <div className="flex gap-3 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-500/15 text-violet-400">
                    <PartyPopper className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-white">Event created</h2>
                    <p className="text-sm text-neutral-400 mt-0.5 truncate" title={eventName}>
                      {eventName}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-white transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="px-5 py-4 space-y-4">
                <p className="text-sm text-neutral-300 leading-relaxed">
                  Share this link with teams so they can submit their GitHub repository for analysis.
                </p>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    Submission link
                  </label>
                  <div className="flex gap-2">
                    <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2.5">
                      <Link2 className="h-4 w-4 shrink-0 text-neutral-500" />
                      <span className="truncate text-xs text-neutral-300 font-mono">{shareUrl || "…"}</span>
                    </div>
                    <button
                      type="button"
                      onClick={copyLink}
                      disabled={!shareUrl}
                      className={cn(
                        "shrink-0 flex items-center gap-1.5 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors",
                        copied
                          ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                          : "bg-violet-600 text-white hover:bg-violet-500 border border-transparent disabled:opacity-40",
                      )}
                    >
                      {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      {copied ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={onClose}
                  className="w-full rounded-xl bg-neutral-800 py-2.5 text-sm font-medium text-white hover:bg-neutral-700 transition-colors"
                >
                  Go to dashboard
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
