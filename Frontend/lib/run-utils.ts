import type { AnalysisRunState, PlanTask, RunSubtaskState } from "./types";

const PHASE_DEPS: Record<string, string[]> = {
  phase1: [],
  phase2: ["1"],
  phase3: ["2"],
  outputs: ["3"],
};

export function mapRunToPlan(run: AnalysisRunState): PlanTask[] {
  return run.phases.map((phase) => ({
    id: phase.id,
    title: phase.title,
    description: phase.description,
    status: phase.status,
    dependencies: PHASE_DEPS[phase.id] ?? [],
    subtasks: phase.subtasks.map((s: RunSubtaskState) => ({
      id: s.id,
      title: s.title,
      description: s.detail || s.description,
      status: s.status,
      tools: s.badges,
      activity: s.activity_log,
    })),
  }));
}
