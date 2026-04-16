"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch, GalleryThumbnails, FileText, Video,
  MonitorPlay, ChevronDown, Check, Shuffle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EventFormData, CriterionState } from "./create-event-wizard";
import { ARTIFACT_CRITERION_IDS } from "./create-event-wizard";

/* ── Criterion definitions ─────────────────────────────────────── */

interface CriterionDef { id: string; label: string; description: string; }

const CRITERIA_BY_ARTIFACT: Record<string, CriterionDef[]> = {
  repo: [
    { id: "repo_completeness",  label: "Project Completeness",           description: "Are the main objectives and key features fully implemented?" },
    { id: "repo_impl_quality",  label: "Implementation Quality",          description: "Does the project work correctly, efficiently, and meet requirements?" },
    { id: "repo_code_quality",  label: "Code Quality",                    description: "Is the code clean, modular, readable, and maintainable?" },
    { id: "repo_documentation", label: "Documentation & Reproducibility", description: "Does the README clearly explain setup, usage, and can the project be run easily?" },
    { id: "repo_depth",         label: "Technical Depth / Innovation",    description: "Does the repo show strong engineering effort, complexity, or originality?" },
  ],
  presentation: [
    { id: "pres_clarity",   label: "Clarity of Problem and Objective", description: "Is the problem clearly introduced and are the project goals easy to understand?" },
    { id: "pres_structure", label: "Structure and Story Flow",          description: "Does the presentation move logically from problem to solution to results?" },
    { id: "pres_solution",  label: "Explanation of Solution",           description: "Is the proposed system/approach explained clearly and convincingly?" },
    { id: "pres_design",    label: "Visual Design and Readability",     description: "Are the slides clean, engaging, and easy to read?" },
    { id: "pres_impact",    label: "Results and Impact",                description: "Does the deck clearly show outcomes, benefits, or evidence the project works?" },
  ],
  report: [
    { id: "report_problem",     label: "Problem Definition",               description: "Is the problem, context, and objective clearly explained?" },
    { id: "report_methodology", label: "Methodology / Approach",           description: "Is the solution approach described logically and in enough detail?" },
    { id: "report_depth",       label: "Technical Depth",                  description: "Does the report show strong understanding, design choices, and implementation details?" },
    { id: "report_results",     label: "Results and Analysis",             description: "Are outcomes presented clearly and analyzed meaningfully?" },
    { id: "report_writing",     label: "Writing Quality and Organization", description: "Is the report well-structured, clear, and professional?" },
  ],
  demo: [
    { id: "demo_clarity",       label: "Clarity of Demonstration",     description: "Does the video clearly show what the project does?" },
    { id: "demo_coverage",      label: "Feature Coverage",              description: "Are the main features and workflow demonstrated properly?" },
    { id: "demo_functionality", label: "Functionality / Working Proof", description: "Does the demo prove that the project actually works?" },
    { id: "demo_narration",     label: "Explanation and Narration",     description: "Is the walkthrough easy to follow and well explained?" },
    { id: "demo_quality",       label: "Presentation Quality",          description: "Is the video clear, well-paced, and professionally presented?" },
  ],
  live: [
    { id: "live_clarity",       label: "Communication Clarity",                description: "Do the presenters explain the project clearly and confidently?" },
    { id: "live_understanding", label: "Understanding of the Project",          description: "Do they show strong knowledge of the problem, solution, and implementation?" },
    { id: "live_delivery",      label: "Delivery and Engagement",               description: "Is the presentation confident, professional, and engaging?" },
    { id: "live_qa",            label: "Handling of Questions",                 description: "Are answers accurate, thoughtful, and well supported?" },
    { id: "live_coordination",  label: "Team Coordination and Time Management", description: "Are speaking roles balanced and is the presentation well managed within time?" },
  ],
};

const ARTIFACT_META: Record<string, { label: string; Icon: React.ComponentType<{ className?: string }> }> = {
  repo:         { label: "GitHub Repository", Icon: GitBranch },
  presentation: { label: "Presentation",      Icon: GalleryThumbnails },
  report:       { label: "Project Report",    Icon: FileText },
  demo:         { label: "Demo Video",         Icon: Video },
  live:         { label: "Live Presentation", Icon: MonitorPlay },
};

const MAX_PER_ARTIFACT = 5;

/* ── Helpers ───────────────────────────────────────────────────── */

function getArtifactTotal(artifactId: string, criteria: Record<string, CriterionState>): number {
  return (CRITERIA_BY_ARTIFACT[artifactId] ?? [])
    .filter(d => criteria[d.id]?.selected)
    .reduce((sum, d) => sum + (criteria[d.id]?.weight ?? 0), 0);
}

function getArtifactSelectedCount(artifactId: string, criteria: Record<string, CriterionState>): number {
  return (CRITERIA_BY_ARTIFACT[artifactId] ?? []).filter(d => criteria[d.id]?.selected).length;
}

/* ── Component ─────────────────────────────────────────────────── */

interface Step3Props {
  data: EventFormData;
  onChange: (partial: Partial<EventFormData>) => void;
}

export function Step3Judging({ data, onChange }: Step3Props) {
  const artifactTabs = data.artifacts.filter(a => a in ARTIFACT_CRITERION_IDS);
  const [openArtifact, setOpenArtifact] = useState<string | null>(artifactTabs[0] ?? null);

  const updateCriteria = (updates: Record<string, CriterionState>) =>
    onChange({ criteria: { ...data.criteria, ...updates } });

  const toggle = (artifactId: string, criterionId: string) => {
    const current     = data.criteria[criterionId];
    const selectedIds = (CRITERIA_BY_ARTIFACT[artifactId] ?? [])
      .filter(d => data.criteria[d.id]?.selected).map(d => d.id);
    if (current.selected && selectedIds.length === 1) return;
    if (!current.selected && selectedIds.length >= MAX_PER_ARTIFACT) return;
    updateCriteria({ [criterionId]: { ...current, selected: !current.selected, weight: 0 } });
  };

  const autoDistribute = (artifactId: string) => {
    const defs     = CRITERIA_BY_ARTIFACT[artifactId] ?? [];
    const selected = defs.filter(d => data.criteria[d.id]?.selected);
    if (selected.length === 0) return;
    const base      = Math.floor(100 / selected.length);
    const remainder = 100 - base * selected.length;
    const updates: Record<string, CriterionState> = {};
    selected.forEach((d, i) => {
      updates[d.id] = { selected: true, weight: base + (i === 0 ? remainder : 0) };
    });
    updateCriteria(updates);
  };

  const setWeight = (criterionId: string, raw: string) => {
    const clamped = Math.max(0, Math.min(100, parseInt(raw) || 0));
    updateCriteria({ [criterionId]: { ...data.criteria[criterionId], weight: clamped } });
  };

  return (
    <div className="flex flex-col gap-3">
      {artifactTabs.map((artifactId) => {
        const meta       = ARTIFACT_META[artifactId];
        const Icon       = meta?.Icon;
        const defs       = CRITERIA_BY_ARTIFACT[artifactId] ?? [];
        const selCount   = getArtifactSelectedCount(artifactId, data.criteria);
        const total      = getArtifactTotal(artifactId, data.criteria);
        const isComplete = total === 100;
        const isOver     = total > 100;
        const isOpen     = openArtifact === artifactId;

        // Per-artifact sequential index
        let idx = 0;

        return (
          <div
            key={artifactId}
            className={cn(
              "rounded-xl border overflow-hidden transition-colors duration-200",
              isOpen
                ? "border-neutral-700"
                : isComplete
                ? "border-emerald-900/50"
                : "border-neutral-800",
            )}
          >
            {/* ── Accordion header ── */}
            <button
              type="button"
              onClick={() => setOpenArtifact(isOpen ? null : artifactId)}
              className={cn(
                "w-full flex items-center gap-3 px-5 py-4 text-left transition-colors",
                isOpen ? "bg-neutral-900" : "bg-neutral-950 hover:bg-neutral-900/60",
              )}
            >
              {/* Icon */}
              <div className={cn(
                "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
                isOpen ? "bg-violet/20" : "bg-neutral-800",
              )}>
                {Icon && <Icon className={cn("h-4 w-4", isOpen ? "text-violet" : "text-neutral-400")} />}
              </div>

              {/* Name */}
              <div className="flex-1 min-w-0">
                <p className={cn(
                  "text-sm font-semibold",
                  isOpen ? "text-white" : "text-neutral-300",
                )}>
                  {meta?.label}
                </p>
              </div>

              {/* Selected count */}
              <p className={cn(
                "flex-shrink-0 text-sm font-medium tabular-nums",
                selCount === defs.length ? "text-neutral-300" : "text-neutral-500",
              )}>
                {selCount} of {defs.length} selected
              </p>

              {/* Chevron */}
              <ChevronDown className={cn(
                "h-4 w-4 flex-shrink-0 text-neutral-500 transition-transform duration-200",
                isOpen && "rotate-180",
              )} />
            </button>

            {/* ── Accordion body ── */}
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-neutral-800">

                    {/* Table */}
                    <table className="w-full table-fixed border-collapse">
                      <colgroup>
                        <col style={{ width: "4%" }}  />
                        <col style={{ width: "24%" }} />
                        <col style={{ width: "58%" }} />
                        <col style={{ width: "14%" }} />
                      </colgroup>

                      {/* Header */}
                      <thead>
                        <tr className="border-b border-neutral-800 bg-neutral-900/40">
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">#</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Criterion</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Description</th>
                          <th className="px-4 py-2.5 text-right text-xs font-semibold text-neutral-400">Weight</th>
                        </tr>
                      </thead>

                      {/* Rows */}
                      <tbody>
                        {defs.map((def, i) => {
                          const state      = data.criteria[def.id];
                          const isSelected = state?.selected ?? false;
                          const weight     = state?.weight ?? 0;
                          const isLast     = i === defs.length - 1;
                          const rowIdx     = isSelected ? ++idx : null;
                          const isMaxed    = !isSelected && selCount >= MAX_PER_ARTIFACT;

                          return (
                            <tr
                              key={def.id}
                              onClick={() => toggle(artifactId, def.id)}
                              className={cn(
                                "transition-colors duration-150",
                                !isLast && "border-b border-neutral-800/60",
                                isSelected
                                  ? "bg-violet/[0.04] cursor-pointer hover:bg-violet/[0.07]"
                                  : isMaxed
                                  ? "opacity-30 cursor-not-allowed"
                                  : "cursor-pointer hover:bg-neutral-900/50",
                              )}
                            >
                              {/* # */}
                              <td className="px-4 py-4 align-top">
                                <span className={cn(
                                  "text-sm font-medium tabular-nums",
                                  isSelected ? "text-white" : "text-neutral-700",
                                )}>
                                  {isSelected ? rowIdx : "—"}
                                </span>
                              </td>

                              {/* Criterion */}
                              <td className="px-4 py-4 align-top">
                                <p className={cn(
                                  "text-sm font-semibold leading-snug",
                                  isSelected ? "text-white" : "text-neutral-600",
                                )}>
                                  {def.label}
                                </p>
                              </td>

                              {/* Description */}
                              <td className="px-4 py-4 align-top">
                                <p className={cn(
                                  "text-sm leading-relaxed",
                                  isSelected ? "text-neutral-400" : "text-neutral-700",
                                )}>
                                  {def.description}
                                </p>
                              </td>

                              {/* Weight */}
                              <td
                                className="px-4 py-4 align-top text-right"
                                onClick={(e) => isSelected && e.stopPropagation()}
                              >
                                {isSelected ? (
                                  <div className="flex items-baseline justify-end gap-0.5">
                                    <input
                                      type="number"
                                      min={0}
                                      max={100}
                                      value={weight === 0 ? "" : weight}
                                      onChange={(e) => setWeight(def.id, e.target.value)}
                                      placeholder="0"
                                      className="w-10 bg-transparent text-right text-sm font-bold text-white tabular-nums outline-none focus:text-violet transition-colors [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                                    />
                                    <span className="text-xs text-neutral-500">%</span>
                                  </div>
                                ) : (
                                  <span className="text-sm text-neutral-700">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>

                    {/* Footer: total + auto-distribute */}
                    <div className={cn(
                      "flex items-center justify-between px-5 py-3 border-t border-neutral-800",
                      isComplete ? "bg-emerald-500/5" : isOver ? "bg-red-500/5" : "bg-neutral-900/30",
                    )}>
                      <button
                        type="button"
                        onClick={() => autoDistribute(artifactId)}
                        className="flex items-center gap-1.5 text-xs font-medium text-neutral-500 transition-colors hover:text-neutral-300"
                      >
                        <Shuffle className="h-3 w-3" />
                        Auto-distribute
                      </button>
                      <span className={cn(
                        "text-sm font-bold tabular-nums",
                        isComplete ? "text-emerald-400" : isOver ? "text-red-400" : "text-amber-400",
                      )}>
                        {isComplete ? "100% ✓" : isOver ? `${total}% — over` : `${total} / 100`}
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </div>
  );
}
