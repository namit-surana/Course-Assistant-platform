"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { AnalyzeCompletedState } from "@/components/analyze/analyze-completed-state";
import { AnalyzeEmptyState } from "@/components/analyze/analyze-empty-state";
import { AnalyzeRunningState } from "@/components/analyze/analyze-running-state";
import type {
  AnalysisRunState,
  CreateRunPayload,
  PlanTask,
  RunSubtaskState,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const PHASE_DEPENDENCIES: Record<string, string[]> = {
  phase1: [],
  phase2: ["1"],
  phase3: ["2"],
  outputs: ["3"],
};

export function RepositoryAnalyzer() {
  const [repoUrl, setRepoUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [run, setRun] = useState<AnalysisRunState | null>(null);
  const [recentRuns, setRecentRuns] = useState<AnalysisRunState[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const planTasks = useMemo(() => mapRunToPlan(run), [run]);
  const failedStep = useMemo(() => findFailedStep(run), [run]);

  useEffect(() => {
    void loadRecentRuns();
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    eventSourceRef.current?.close();

    try {
      const payload: CreateRunPayload = { repo_url: repoUrl.trim() };
      if (branch.trim()) {
        payload.branch = branch.trim();
      }

      const response = await fetch(`${API_BASE_URL}/api/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || "Unable to start repository analysis.");
      }

      const createdRun = (await response.json()) as AnalysisRunState;
      setRun(createdRun);
      setRepoUrl(createdRun.request.repo_url);
      setBranch(createdRun.request.branch || "");
      setRecentRuns((previous) => mergeRuns([createdRun, ...previous]));
      attachEventStream(createdRun.id);
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : "Unable to start repository analysis.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function attachEventStream(runId: string) {
    const source = new EventSource(`${API_BASE_URL}/api/runs/${runId}/stream`);
    eventSourceRef.current = source;

    source.addEventListener("run", (message) => {
      const payload = JSON.parse(message.data) as AnalysisRunState;
      setRun(payload);
      setRecentRuns((previous) => mergeRuns([payload, ...previous]));

      if (payload.status === "completed" || payload.status === "failed") {
        source.close();
      }
    });

    source.onerror = async () => {
      source.close();
      try {
        const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
        if (!response.ok) {
          throw new Error("Unable to refresh the run.");
        }
        const payload = (await response.json()) as AnalysisRunState;
        setRun(payload);
        setRecentRuns((previous) => mergeRuns([payload, ...previous]));
      } catch {
        setError("Lost the live stream connection to the backend.");
      }
    };
  }

  async function loadRecentRuns() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/runs?limit=12`);
      if (!response.ok) {
        throw new Error("Unable to load recent runs.");
      }
      const payload = (await response.json()) as AnalysisRunState[];
      setRecentRuns(mergeRuns(payload));
    } catch {
      // Keep the workspace usable even if recent runs are unavailable.
    }
  }

  async function openRun(runId: string) {
    setError(null);
    eventSourceRef.current?.close();
    try {
      const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
      if (!response.ok) {
        throw new Error("Unable to load the selected run.");
      }
      const payload = (await response.json()) as AnalysisRunState;
      setRun(payload);
      setRepoUrl(payload.request.repo_url);
      setBranch(payload.request.branch || "");
      setRecentRuns((previous) => mergeRuns([payload, ...previous]));
      if (payload.status === "running" || payload.status === "queued") {
        attachEventStream(payload.id);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load the selected run.");
    }
  }

  function startNewAnalysis() {
    eventSourceRef.current?.close();
    setRun(null);
    setError(null);
    setRepoUrl("");
    setBranch("");
  }

  if (!run) {
    return (
      <AnalyzeEmptyState
        repoUrl={repoUrl}
        branch={branch}
        error={error}
        isSubmitting={isSubmitting}
        recentRuns={recentRuns}
        onRepoUrlChange={setRepoUrl}
        onBranchChange={setBranch}
        onSubmit={handleSubmit}
        onOpenRun={openRun}
      />
    );
  }

  if (run.status === "completed") {
    return (
      <AnalyzeCompletedState
        run={run}
        planTasks={planTasks}
        recentRuns={recentRuns}
        onOpenRun={openRun}
        onStartNewAnalysis={startNewAnalysis}
      />
    );
  }

  return (
    <AnalyzeRunningState
      run={run}
      planTasks={planTasks}
      failedStep={failedStep}
      recentRuns={recentRuns}
      onOpenRun={openRun}
      onStartNewAnalysis={startNewAnalysis}
    />
  );
}

function mapRunToPlan(run: AnalysisRunState | null): PlanTask[] {
  if (!run) {
    return [];
  }

  return run.phases.map((phase) => ({
    id: phase.id,
    title: phase.title,
    description: phase.description,
    status: phase.status,
    dependencies: PHASE_DEPENDENCIES[phase.id] ?? [],
    subtasks: phase.subtasks.map((subtask) => mapSubtask(subtask)),
  }));
}

function mapSubtask(subtask: RunSubtaskState) {
  return {
    id: subtask.id,
    title: subtask.title,
    description: subtask.detail || subtask.description,
    status: subtask.status,
    tools: subtask.badges,
    activity: subtask.activity_log,
  };
}

function findFailedStep(run: AnalysisRunState | null) {
  if (!run) {
    return null;
  }

  for (const phase of run.phases) {
    const failedSubtask = phase.subtasks.find((subtask) => subtask.status === "failed");
    if (failedSubtask) {
      return {
        phaseTitle: phase.title,
        subtaskTitle: failedSubtask.title,
        detail: failedSubtask.detail,
      };
    }
  }

  return null;
}

function mergeRuns(runs: AnalysisRunState[]): AnalysisRunState[] {
  const deduped = new Map<string, AnalysisRunState>();
  for (const run of runs) {
    deduped.set(run.id, run);
  }
  return [...deduped.values()].sort((left, right) => {
    const rightTime = Date.parse(right.updated_at ?? "") || 0;
    const leftTime = Date.parse(left.updated_at ?? "") || 0;
    return rightTime - leftTime;
  });
}
