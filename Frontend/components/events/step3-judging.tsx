"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch,
  GalleryThumbnails,
  FileText,
  Video,
  MonitorPlay,
  ChevronDown,
  Shuffle,
  Plus,
  Trash2,
  RotateCcw,
  Wand2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { EventFormData, CriterionState } from "./create-event-wizard";
import { ARTIFACT_CRITERION_IDS } from "./create-event-wizard";

interface CriterionDef {
  id: string;
  label: string;
  description: string;
}

type EditableCriterion = CriterionDef & CriterionState;

const CRITERIA_BY_ARTIFACT: Record<string, CriterionDef[]> = {
  repo: [
    { id: "repo_completeness", label: "Project Completeness", description: "Are the main objectives and key features fully implemented?" },
    { id: "repo_impl_quality", label: "Implementation Quality", description: "Does the project work correctly, efficiently, and meet requirements?" },
    { id: "repo_code_quality", label: "Code Quality", description: "Is the code clean, modular, readable, and maintainable?" },
    { id: "repo_documentation", label: "Documentation & Reproducibility", description: "Does the README clearly explain setup, usage, and can the project be run easily?" },
    { id: "repo_depth", label: "Technical Depth / Innovation", description: "Does the repo show strong engineering effort, complexity, or originality?" },
  ],
  presentation: [
    { id: "pres_clarity", label: "Clarity of Problem and Objective", description: "Is the problem clearly introduced and are the project goals easy to understand?" },
    { id: "pres_structure", label: "Structure and Story Flow", description: "Does the presentation move logically from problem to solution to results?" },
    { id: "pres_solution", label: "Explanation of Solution", description: "Is the proposed system/approach explained clearly and convincingly?" },
    { id: "pres_design", label: "Visual Design and Readability", description: "Are the slides clean, engaging, and easy to read?" },
    { id: "pres_impact", label: "Results and Impact", description: "Does the deck clearly show outcomes, benefits, or evidence the project works?" },
  ],
  report: [
    { id: "report_problem", label: "Problem Definition", description: "Is the problem, context, and objective clearly explained?" },
    { id: "report_methodology", label: "Methodology / Approach", description: "Is the solution approach described logically and in enough detail?" },
    { id: "report_depth", label: "Technical Depth", description: "Does the report show strong understanding, design choices, and implementation details?" },
    { id: "report_results", label: "Results and Analysis", description: "Are outcomes presented clearly and analyzed meaningfully?" },
    { id: "report_writing", label: "Writing Quality and Organization", description: "Is the report well-structured, clear, and professional?" },
  ],
  demo: [
    { id: "demo_clarity", label: "Clarity of Demonstration", description: "Does the video clearly show what the project does?" },
    { id: "demo_coverage", label: "Feature Coverage", description: "Are the main features and workflow demonstrated properly?" },
    { id: "demo_functionality", label: "Functionality / Working Proof", description: "Does the demo prove that the project actually works?" },
    { id: "demo_narration", label: "Explanation and Narration", description: "Is the walkthrough easy to follow and well explained?" },
    { id: "demo_quality", label: "Presentation Quality", description: "Is the video clear, well-paced, and professionally presented?" },
  ],
  live: [
    { id: "live_clarity", label: "Communication Clarity", description: "Do the presenters explain the project clearly and confidently?" },
    { id: "live_understanding", label: "Understanding of the Project", description: "Do they show strong knowledge of the problem, solution, and implementation?" },
    { id: "live_delivery", label: "Delivery and Engagement", description: "Is the presentation confident, professional, and engaging?" },
    { id: "live_qa", label: "Handling of Questions", description: "Are answers accurate, thoughtful, and well supported?" },
    { id: "live_coordination", label: "Team Coordination and Time Management", description: "Are speaking roles balanced and is the presentation well managed within time?" },
  ],
};

const ARTIFACT_META: Record<string, { label: string; Icon: React.ComponentType<{ className?: string }> }> = {
  repo: { label: "GitHub Repository", Icon: GitBranch },
  presentation: { label: "Presentation", Icon: GalleryThumbnails },
  report: { label: "Project Report", Icon: FileText },
  demo: { label: "Demo Video", Icon: Video },
  live: { label: "Live Presentation", Icon: MonitorPlay },
};

const MAX_PER_ARTIFACT = 10;

interface Step3Props {
  data: EventFormData;
  onChange: (partial: Partial<EventFormData>) => void;
}

export function Step3Judging({ data, onChange }: Step3Props) {
  const artifactTabs = data.artifacts.filter((a) => a in ARTIFACT_CRITERION_IDS);

  const [openArtifact, setOpenArtifact] = useState<string | null>(artifactTabs[0] ?? null);
  const [addingArtifact, setAddingArtifact] = useState<string | null>(null);

  const [rubricMode, setRubricMode] = useState<
    Record<string, "suggested" | "custom" | "scratch">
  >({});

  const [newCriterion, setNewCriterion] = useState({
    label: "",
    description: "",
    weight: "",
  });

  const updateCriteria = (updates: Record<string, CriterionState>) => {
    onChange({ criteria: { ...data.criteria, ...updates } });
  };

  const getDefs = (artifactId: string): EditableCriterion[] => {
    return Object.entries(data.criteria)
      .filter(([, c]) => c.artifactId === artifactId)
      .map(([id, c]) => ({
        id,
        label: c.label ?? "",
        description: c.description ?? "",
        selected: c.selected,
        weight: c.weight,
        artifactId: c.artifactId,
      }));
  };

  const removeArtifactCriteria = useCallback((artifactId: string) => {
    const updated = { ...data.criteria };

    Object.entries(updated).forEach(([id, c]) => {
      if (c.artifactId === artifactId) {
        delete updated[id];
      }
    });

    return updated;
  }, [data.criteria]);

  const loadSuggestedCriteria = useCallback((artifactId: string) => {
    const suggested = CRITERIA_BY_ARTIFACT[artifactId] ?? [];
    const updated = removeArtifactCriteria(artifactId);

    suggested.forEach((d) => {
      updated[d.id] = {
        selected: true,
        weight: 0,
        label: d.label,
        description: d.description,
        artifactId,
      };
    });

    onChange({ criteria: updated });
    setRubricMode((prev) => ({ ...prev, [artifactId]: "suggested" }));
  }, [onChange, removeArtifactCriteria, setRubricMode]);

  const createFromScratch = (artifactId: string) => {
    const updated = removeArtifactCriteria(artifactId);

    onChange({ criteria: updated });
    setRubricMode((prev) => ({ ...prev, [artifactId]: "scratch" }));
    setAddingArtifact(artifactId);
    setNewCriterion({ label: "", description: "", weight: "" });
  };

  const artifactsKey = useMemo(() => data.artifacts.join(","), [data.artifacts]);

  useEffect(() => {
    artifactTabs.forEach((artifactId) => {
      const existing = Object.values(data.criteria).filter(
        (c) => c.artifactId === artifactId
      );

      if (existing.length === 0 && rubricMode[artifactId] !== "scratch") {
        loadSuggestedCriteria(artifactId);
      }
    });
  }, [artifactTabs, data.criteria, artifactsKey, loadSuggestedCriteria, rubricMode]);

  const getArtifactTotal = (artifactId: string) => {
    return getDefs(artifactId)
      .filter((d) => d.selected)
      .reduce((sum, d) => sum + (d.weight ?? 0), 0);
  };

  const getArtifactSelectedCount = (artifactId: string) => {
    return getDefs(artifactId).filter((d) => d.selected).length;
  };

  const toggle = (artifactId: string, criterionId: string) => {
    const defs = getDefs(artifactId);
    const current = data.criteria[criterionId];
    const selectedIds = defs.filter((d) => d.selected).map((d) => d.id);

    if (!current) return;
    if (current.selected && selectedIds.length === 1) return;
    if (!current.selected && selectedIds.length >= MAX_PER_ARTIFACT) return;

    updateCriteria({
      [criterionId]: {
        ...current,
        selected: !current.selected,
        weight: !current.selected ? current.weight : 0,
      },
    });

    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const autoDistribute = (artifactId: string) => {
    const selected = getDefs(artifactId).filter((d) => d.selected);
    if (selected.length === 0) return;

    const base = Math.floor(100 / selected.length);
    const remainder = 100 - base * selected.length;
    const updates: Record<string, CriterionState> = {};

    selected.forEach((d, i) => {
      updates[d.id] = {
        ...data.criteria[d.id],
        selected: true,
        weight: base + (i === 0 ? remainder : 0),
      };
    });

    updateCriteria(updates);
    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const setWeight = (artifactId: string, criterionId: string, raw: string) => {
    const clamped = Math.max(0, Math.min(100, parseInt(raw) || 0));

    updateCriteria({
      [criterionId]: {
        ...data.criteria[criterionId],
        weight: clamped,
      },
    });

    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const updateLabel = (artifactId: string, criterionId: string, value: string) => {
    updateCriteria({
      [criterionId]: {
        ...data.criteria[criterionId],
        label: value,
      },
    });

    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const updateDescription = (artifactId: string, criterionId: string, value: string) => {
    updateCriteria({
      [criterionId]: {
        ...data.criteria[criterionId],
        description: value,
      },
    });

    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const saveNewCriterion = (artifactId: string) => {
    if (!newCriterion.label.trim()) return;

    const id = `${artifactId}_custom_${Date.now()}`;

    updateCriteria({
      [id]: {
        selected: true,
        weight: Math.max(0, Math.min(100, parseInt(newCriterion.weight) || 0)),
        label: newCriterion.label.trim(),
        description: newCriterion.description.trim(),
        artifactId,
      },
    });

    setNewCriterion({
      label: "",
      description: "",
      weight: "",
    });

    setAddingArtifact(null);
    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  const cancelNewCriterion = () => {
    setNewCriterion({
      label: "",
      description: "",
      weight: "",
    });

    setAddingArtifact(null);
  };

  const deleteCriterion = (artifactId: string, criterionId: string) => {
    const updated = { ...data.criteria };
    delete updated[criterionId];

    onChange({ criteria: updated });
    setRubricMode((prev) => ({ ...prev, [artifactId]: "custom" }));
  };

  return (
    <div className="flex flex-col gap-3">
      {artifactTabs.map((artifactId) => {
        const meta = ARTIFACT_META[artifactId];
        const Icon = meta?.Icon;
        const defs = getDefs(artifactId);
        const selCount = getArtifactSelectedCount(artifactId);
        const total = getArtifactTotal(artifactId);
        const isComplete = total === 100;
        const isOver = total > 100;
        const isOpen = openArtifact === artifactId;
        const mode = rubricMode[artifactId] ?? "suggested";

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
                : "border-neutral-800"
            )}
          >
            <button
              type="button"
              onClick={() => setOpenArtifact(isOpen ? null : artifactId)}
              className={cn(
                "w-full flex items-center gap-3 px-5 py-4 text-left transition-colors",
                isOpen ? "bg-neutral-900" : "bg-neutral-950 hover:bg-neutral-900/60"
              )}
            >
              <div
                className={cn(
                  "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
                  isOpen ? "bg-violet/20" : "bg-neutral-800"
                )}
              >
                {Icon && (
                  <Icon
                    className={cn(
                      "h-4 w-4",
                      isOpen ? "text-violet" : "text-neutral-400"
                    )}
                  />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <p className={cn("text-sm font-semibold", isOpen ? "text-white" : "text-neutral-300")}>
                  {meta?.label}
                </p>
              </div>

              <span
                className={cn(
                  "rounded-full px-2 py-1 text-[11px] font-medium capitalize",
                  mode === "suggested"
                    ? "bg-neutral-800 text-neutral-400"
                    : mode === "scratch"
                    ? "bg-violet/10 text-violet"
                    : "bg-amber-500/10 text-amber-400"
                )}
              >
                {mode}
              </span>

              <p className="flex-shrink-0 text-sm font-medium tabular-nums text-neutral-500">
                {selCount} selected
              </p>

              <ChevronDown
                className={cn(
                  "h-4 w-4 flex-shrink-0 text-neutral-500 transition-transform duration-200",
                  isOpen && "rotate-180"
                )}
              />
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div className="border-t border-neutral-800">
                    <div className="flex flex-col gap-3 bg-neutral-950 px-5 py-4">
                      <p className="text-xs text-neutral-500">
                        Start with suggested criteria, customize them, or create a completely new rubric.
                      </p>

                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                        <button
                          type="button"
                          onClick={() => loadSuggestedCriteria(artifactId)}
                          className={cn(
                            "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                            mode === "suggested"
                              ? "border-violet/50 bg-violet/10 text-violet"
                              : "border-neutral-800 text-neutral-400 hover:border-violet hover:text-white"
                          )}
                        >
                          <RotateCcw className="mr-1 inline h-3 w-3" />
                          Use suggested
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            setRubricMode((prev) => ({
                              ...prev,
                              [artifactId]: "custom",
                            }))
                          }
                          className={cn(
                            "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                            mode === "custom"
                              ? "border-amber-500/50 bg-amber-500/10 text-amber-400"
                              : "border-neutral-800 text-neutral-400 hover:border-violet hover:text-white"
                          )}
                        >
                          <Wand2 className="mr-1 inline h-3 w-3" />
                          Customize
                        </button>

                        <button
                          type="button"
                          onClick={() => createFromScratch(artifactId)}
                          className={cn(
                            "rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                            mode === "scratch"
                              ? "border-violet/50 bg-violet/10 text-violet"
                              : "border-violet/40 text-violet hover:bg-violet/10"
                          )}
                        >
                          <Plus className="mr-1 inline h-3 w-3" />
                          Create from scratch
                        </button>
                      </div>

                      <div className="flex items-center justify-between gap-3">
                        <button
                          type="button"
                          onClick={() => setAddingArtifact(artifactId)}
                          className="flex items-center gap-1.5 rounded-lg border border-violet/40 px-3 py-1.5 text-xs font-medium text-violet hover:bg-violet/10"
                        >
                          <Plus className="h-3 w-3" />
                          Add completely new criterion
                        </button>

                        <span
                          className={cn(
                            "text-xs font-semibold tabular-nums",
                            total === 100
                              ? "text-emerald-400"
                              : total > 100
                              ? "text-red-400"
                              : "text-amber-400"
                          )}
                        >
                          Total: {total}/100
                        </span>
                      </div>

                      <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
                        <div
                          className={cn(
                            "h-full transition-all",
                            total === 100
                              ? "bg-emerald-500"
                              : total > 100
                              ? "bg-red-500"
                              : "bg-amber-500"
                          )}
                          style={{ width: `${Math.min(total, 100)}%` }}
                        />
                      </div>

                      {total !== 100 && (
                        <p
                          className={cn(
                            "text-xs",
                            total > 100 ? "text-red-400" : "text-amber-400"
                          )}
                        >
                          {total > 100
                            ? "Weights are over 100%. Reduce some values before creating the event."
                            : "Weights must total exactly 100% before creating the event."}
                        </p>
                      )}
                    </div>

                    {addingArtifact === artifactId && (
                      <div className="mx-5 mb-4 mt-4 rounded-xl border border-violet/30 bg-neutral-950 p-4">
                        <p className="mb-1 text-sm font-semibold text-white">
                          Add completely new criterion
                        </p>

                        <p className="mb-4 text-xs text-neutral-500">
                          Create a custom evaluation rule with its own name, description, and weight.
                        </p>

                        <div className="grid gap-3">
                          <input
                            value={newCriterion.label}
                            onChange={(e) =>
                              setNewCriterion((prev) => ({
                                ...prev,
                                label: e.target.value,
                              }))
                            }
                            placeholder="Criterion name, e.g. Creativity and Originality"
                            className="w-full rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-white outline-none placeholder:text-neutral-600 focus:border-violet"
                          />

                          <textarea
                            value={newCriterion.description}
                            onChange={(e) =>
                              setNewCriterion((prev) => ({
                                ...prev,
                                description: e.target.value,
                              }))
                            }
                            placeholder="Description, e.g. Does the project show a unique and creative approach?"
                            rows={3}
                            className="w-full resize-none rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-white outline-none placeholder:text-neutral-600 focus:border-violet"
                          />

                          <div className="flex items-center gap-2">
                            <input
                              type="number"
                              min={0}
                              max={100}
                              value={newCriterion.weight}
                              onChange={(e) =>
                                setNewCriterion((prev) => ({
                                  ...prev,
                                  weight: e.target.value,
                                }))
                              }
                              placeholder="Weight"
                              className="w-28 rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-white outline-none placeholder:text-neutral-600 focus:border-violet"
                            />
                            <span className="text-sm text-neutral-500">%</span>
                          </div>
                        </div>

                        <div className="mt-4 flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={cancelNewCriterion}
                            className="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-400 hover:text-white"
                          >
                            Cancel
                          </button>

                          <button
                            type="button"
                            onClick={() => saveNewCriterion(artifactId)}
                            disabled={!newCriterion.label.trim()}
                            className="rounded-lg bg-violet px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            Add Criterion
                          </button>
                        </div>
                      </div>
                    )}

                    <table className="w-full table-fixed border-collapse">
                      <colgroup>
                        <col style={{ width: "4%" }} />
                        <col style={{ width: "24%" }} />
                        <col style={{ width: "48%" }} />
                        <col style={{ width: "14%" }} />
                        <col style={{ width: "10%" }} />
                      </colgroup>

                      <thead>
                        <tr className="border-b border-neutral-800 bg-neutral-900/40">
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">#</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Criterion</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-neutral-400">Description</th>
                          <th className="px-4 py-2.5 text-right text-xs font-semibold text-neutral-400">Weight</th>
                          <th className="px-4 py-2.5 text-right text-xs font-semibold text-neutral-400">Action</th>
                        </tr>
                      </thead>

                      <tbody>
                        {defs.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-5 py-10 text-center">
                              <p className="text-sm font-medium text-neutral-300">
                                No criteria added yet.
                              </p>
                              <p className="mt-1 text-xs text-neutral-500">
                                Add a completely new criterion or use the suggested rubric.
                              </p>
                            </td>
                          </tr>
                        ) : (
                          defs.map((def, i) => {
                            const state = data.criteria[def.id];
                            const isSelected = state?.selected ?? false;
                            const weight = state?.weight ?? 0;
                            const rowIdx = isSelected ? ++idx : null;
                            const isLast = i === defs.length - 1;
                            const isMaxed = !isSelected && selCount >= MAX_PER_ARTIFACT;

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
                                    : "cursor-pointer hover:bg-neutral-900/50"
                                )}
                              >
                                <td className="px-4 py-4 align-top">
                                  <span
                                    className={cn(
                                      "text-sm font-medium tabular-nums",
                                      isSelected ? "text-white" : "text-neutral-700"
                                    )}
                                  >
                                    {isSelected ? rowIdx : "—"}
                                  </span>
                                </td>

                                <td
                                  className="px-4 py-4 align-top"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <input
                                    value={def.label}
                                    onChange={(e) =>
                                      updateLabel(artifactId, def.id, e.target.value)
                                    }
                                    className={cn(
                                      "w-full bg-transparent text-sm font-semibold leading-snug outline-none",
                                      isSelected
                                        ? "text-white focus:text-violet"
                                        : "text-neutral-600"
                                    )}
                                  />
                                </td>

                                <td
                                  className="px-4 py-4 align-top"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <textarea
                                    value={def.description}
                                    onChange={(e) =>
                                      updateDescription(artifactId, def.id, e.target.value)
                                    }
                                    rows={2}
                                    className={cn(
                                      "w-full resize-none bg-transparent text-sm leading-relaxed outline-none",
                                      isSelected
                                        ? "text-neutral-400 focus:text-neutral-200"
                                        : "text-neutral-700"
                                    )}
                                  />
                                </td>

                                <td
                                  className="px-4 py-4 align-top text-right"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  {isSelected ? (
                                    <div className="flex items-baseline justify-end gap-0.5">
                                      <input
                                        type="number"
                                        min={0}
                                        max={100}
                                        value={weight === 0 ? "" : weight}
                                        onChange={(e) =>
                                          setWeight(artifactId, def.id, e.target.value)
                                        }
                                        placeholder="0"
                                        className="w-10 bg-transparent text-right text-sm font-bold text-white tabular-nums outline-none focus:text-violet transition-colors [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                                      />
                                      <span className="text-xs text-neutral-500">%</span>
                                    </div>
                                  ) : (
                                    <span className="text-sm text-neutral-700">—</span>
                                  )}
                                </td>

                                <td
                                  className="px-4 py-4 align-top text-right"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <button
                                    type="button"
                                    onClick={() => deleteCriterion(artifactId, def.id)}
                                    className="inline-flex items-center justify-center rounded-md p-1.5 text-neutral-600 hover:bg-red-500/10 hover:text-red-400"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>

                    <div
                      className={cn(
                        "flex items-center justify-between px-5 py-3 border-t border-neutral-800",
                        isComplete
                          ? "bg-emerald-500/5"
                          : isOver
                          ? "bg-red-500/5"
                          : "bg-neutral-900/30"
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => autoDistribute(artifactId)}
                        disabled={selCount === 0}
                        className="flex items-center gap-1.5 text-xs font-medium text-neutral-500 transition-colors hover:text-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <Shuffle className="h-3 w-3" />
                        Auto-distribute
                      </button>

                      <span
                        className={cn(
                          "text-sm font-bold tabular-nums",
                          isComplete
                            ? "text-emerald-400"
                            : isOver
                            ? "text-red-400"
                            : "text-amber-400"
                        )}
                      >
                        {isComplete
                          ? "100% ✓"
                          : isOver
                          ? `${total}% — over`
                          : `${total} / 100`}
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