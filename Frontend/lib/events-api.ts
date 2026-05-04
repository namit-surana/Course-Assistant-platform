import type { EvalEvent, Submission, WorkerSubmissionDetail } from "./types";
import { mapWorkerSubmissionToRun } from "./backend-submissions";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

interface BackendEvent {
  id: string;
  name: string;
  type: EvalEvent["type"];
  status: EvalEvent["status"];
  description?: string | null;
  submission_deadline?: string | null;
  judging_deadline?: string | null;
  artifacts: string[];
  criteria_config: Record<string, unknown>;
  teams_total: number;
  teams_evaluated: number;
  created_at: string;
}

export interface CreateEventInput {
  name: string;
  type: EvalEvent["type"];
  status?: EvalEvent["status"];
  description?: string;
  submissionDeadline?: string;
  judgingDeadline?: string;
  artifacts: string[];
  criteriaConfig: Record<string, unknown>;
}

export async function fetchEvents(): Promise<EvalEvent[]> {
  const response = await fetch(`${API_BASE_URL}/api/events`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load events.");
  }
  const events = (await response.json()) as BackendEvent[];
  return events.map(mapBackendEvent);
}

export async function createEvent(input: CreateEventInput): Promise<EvalEvent> {
  const response = await fetch(`${API_BASE_URL}/api/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: input.name,
      type: input.type,
      status: input.status || "active",
      description: input.description,
      submission_deadline: input.submissionDeadline || null,
      judging_deadline: input.judgingDeadline || input.submissionDeadline || null,
      artifacts: input.artifacts,
      criteria_config: input.criteriaConfig,
    }),
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to create event.");
  }
  return mapBackendEvent((await response.json()) as BackendEvent);
}

export async function fetchEventSubmissions(eventId: string): Promise<Submission[]> {
  const response = await fetch(`${API_BASE_URL}/api/submissions/events/${eventId}/items`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Unable to load submissions.");
  }
  const submissions = (await response.json()) as WorkerSubmissionDetail[];
  return submissions.map((submission) => {
    const videoArtifact = submission.artifacts.find((artifact) => artifact.kind === "video");
    const pptArtifact = submission.artifacts.find((artifact) => artifact.kind === "ppt");
    const run = mapWorkerSubmissionToRun(submission, {
      id: submission.id,
      revision: 0,
      status: submission.status,
      request: {
        repo_url: submission.repo_url || "",
        branch: submission.branch || undefined,
      },
      phases: [],
      events: [],
    });
    return {
      id: submission.id,
      eventId,
      teamName: submission.team_name,
      repoUrl: submission.repo_url || "",
      branch: submission.branch || undefined,
      runId: submission.id,
      run,
      workerSubmissionId: submission.id,
      pptFileName: pptArtifact?.file_name || undefined,
      videoFileName: videoArtifact?.file_name || undefined,
      videoObjectKey: videoArtifact?.object_key || undefined,
      videoAnalysisStatus: "idle",
      videoAnalysisResult: null,
      createdAt: submission.created_at,
    };
  });
}

function mapBackendEvent(event: BackendEvent): EvalEvent {
  return {
    id: event.id,
    name: event.name,
    type: event.type,
    status: event.status,
    teamsTotal: event.teams_total,
    teamsEvaluated: event.teams_evaluated,
    submissionDeadline: event.submission_deadline || "",
    judgingDeadline: event.judging_deadline || event.submission_deadline || "",
    createdAt: event.created_at.split("T")[0] || event.created_at,
  };
}
