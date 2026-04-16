"use client";

import { motion } from "framer-motion";
import { GitBranch, GalleryThumbnails, FileText, Video, MonitorPlay } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EventFormData } from "./create-event-wizard";

const ARTIFACTS = [
  {
    id: "repo",
    label: "GitHub Repository",
    description: "Source code and commits",
    icon: GitBranch,
  },
  {
    id: "presentation",
    label: "Presentation",
    description: "PPT, PDF slide deck",
    icon: GalleryThumbnails,
  },
  {
    id: "report",
    label: "Project Report",
    description: "Written documentation",
    icon: FileText,
  },
  {
    id: "demo",
    label: "Demo Video",
    description: "Recorded walkthrough",
    icon: Video,
  },
  {
    id: "live",
    label: "Live Presentation",
    description: "Scheduled slot",
    icon: MonitorPlay,
  },
] as const;

type ArtifactId = (typeof ARTIFACTS)[number]["id"];

interface Step2Props {
  data: EventFormData;
  onChange: (data: Partial<EventFormData>) => void;
}

export function Step2Artifacts({ data, onChange }: Step2Props) {
  const toggle = (id: ArtifactId) => {
    const current = data.artifacts;
    const next = current.includes(id)
      ? current.filter((a) => a !== id)
      : [...current, id];
    onChange({ artifacts: next });
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Select what teams will be required to submit. You can change this later.
      </p>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {ARTIFACTS.map((artifact) => {
          const Icon = artifact.icon;
          const selected = data.artifacts.includes(artifact.id);

          return (
            <motion.button
              key={artifact.id}
              type="button"
              onClick={() => toggle(artifact.id)}
              whileTap={{ scale: 0.97 }}
              className={cn(
                "relative flex items-center gap-4 rounded-xl border p-4 text-left transition-all",
                selected
                  ? "border-violet bg-violet/8 shadow-[0_0_16px_oklch(0.65_0.22_280_/_15%)]"
                  : "border-border bg-muted/20 hover:border-border/60 hover:bg-muted/30",
              )}
            >
              {/* Selected indicator */}
              {selected && (
                <motion.div
                  layoutId={`artifact-check-${artifact.id}`}
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-violet"
                >
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </motion.div>
              )}

              <div className={cn(
                "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
                selected ? "bg-violet/15" : "bg-muted/50",
              )}>
                <Icon className={cn("h-5 w-5", selected ? "text-violet" : "text-muted-foreground")} />
              </div>

              <div>
                <p className={cn("text-sm font-medium", selected ? "text-foreground" : "text-foreground/80")}>
                  {artifact.label}
                </p>
                <p className="text-xs text-muted-foreground">{artifact.description}</p>
              </div>
            </motion.button>
          );
        })}
      </div>

      {data.artifacts.length === 0 && (
        <p className="text-center text-xs text-danger/80 mt-1">
          Select at least one artifact type
        </p>
      )}
    </div>
  );
}
