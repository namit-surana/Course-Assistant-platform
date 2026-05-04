import type {
  AnalysisRunState,
  AnalyzeResponse,
  RubricCriterionInput,
  WorkerArtifactInput,
  WorkerSubmissionDetail,
  WorkerSubmissionResponse,
  WorkerVideoAnalysisJob,
  WorkerVideoAnalysisStartResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export const DEFAULT_RUBRIC_TEXT = JSON.stringify(
  [
    {
      category: "Problem and motivation",
      description: "The project explains the problem, target users, and why the solution matters.",
      max_score: 10,
    },
    {
      category: "Technical implementation",
      description: "The implementation is complete, technically sound, and appropriate for the project scope.",
      max_score: 10,
    },
    {
      category: "Presentation clarity",
      description: "The presentation communicates architecture, workflow, results, and limitations clearly.",
      max_score: 10,
    },
  ],
  null,
  2,
);

export function parseRubricCriteria(text: string): RubricCriterionInput[] {
  const parsed = JSON.parse(text) as RubricCriterionInput[];
  if (!Array.isArray(parsed)) {
    throw new Error("Rubric must be a JSON array.");
  }
  return parsed.map((item) => ({
    category: String(item.category || "").trim(),
    description: String(item.description || "").trim(),
    max_score: Number(item.max_score),
  }));
}

export async function submitWorkerProject({
  teamName,
  repoUrl,
  branch,
  pptFile,
  videoFile,
  rubricCriteria,
  eventId,
}: {
  teamName: string;
  repoUrl: string;
  branch?: string;
  pptFile?: File | null;
  videoFile?: File | null;
  rubricCriteria: RubricCriterionInput[];
  eventId?: string;
}) {
  const artifacts: WorkerArtifactInput[] = [];
  if (pptFile) {
    const uploaded = await uploadArtifact(pptFile, "ppt");
    artifacts.push(uploaded);
  }
  if (videoFile) {
    const uploaded = await uploadArtifact(videoFile, "video");
    artifacts.push(uploaded);
  }

  const response = await fetch(`${API_BASE_URL}/api/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      event_id: eventId,
      team_name: teamName,
      repo_url: repoUrl,
      branch: branch || undefined,
      rubric_criteria: rubricCriteria,
      artifacts,
    }),
  });

  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Failed to submit project.");
  }

  const submission = (await response.json()) as WorkerSubmissionResponse;
  return {
    submission,
    run: buildWorkerRun({
      id: submission.analysis_job_id,
      repoUrl,
      branch,
      status: submission.status,
      activity: submission.queued
        ? "Queued for worker analysis"
        : "Saved locally; SQS_QUEUE_URL is not configured.",
    }),
  };
}

export async function fetchWorkerSubmission(submissionId: string): Promise<WorkerSubmissionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/submissions/${submissionId}`);
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to load submission status.");
  }
  return (await response.json()) as WorkerSubmissionDetail;
}

export async function startWorkerSubmissionVideoAnalysis({
  submissionId,
  assignmentTitle,
  requiredFeatures,
}: {
  submissionId: string;
  assignmentTitle?: string;
  requiredFeatures?: string[];
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/submissions/${submissionId}/video-analysis/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      assignment_title: assignmentTitle || "Course project demo",
      required_features: requiredFeatures || [],
    }),
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start video analysis.");
  }
  return (await response.json()) as WorkerVideoAnalysisStartResponse;
}

export async function fetchWorkerVideoAnalysisJob(jobId: string): Promise<WorkerVideoAnalysisJob> {
  const response = await fetch(`${API_BASE_URL}/api/video-analysis/jobs/${jobId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to load video analysis job.");
  }
  return (await response.json()) as WorkerVideoAnalysisJob;
}

export function mapWorkerSubmissionToRun(
  detail: WorkerSubmissionDetail,
  previousRun: AnalysisRunState,
): AnalysisRunState {
  const repositoryResult = detail.feedback?.raw_result?.repository;
  const fallbackResult: AnalyzeResponse | undefined =
    repositoryResult ||
    (detail.feedback
      ? {
          status: "success",
          repo_url: detail.repo_url || previousRun.request.repo_url,
          owner: "",
          repo: "",
          branch: detail.branch || previousRun.request.branch || "",
        }
      : undefined);

  return buildWorkerRun({
    id: previousRun.id,
    repoUrl: detail.repo_url || previousRun.request.repo_url,
    branch: detail.branch || previousRun.request.branch,
    status: detail.status,
    error: detail.error_message || undefined,
    activity: activityForStatus(detail.status),
    result: fallbackResult,
    summary: detail.feedback?.summary || undefined,
    startedAt: previousRun.started_at,
  });
}

async function uploadArtifact(file: File, kind: WorkerArtifactInput["kind"]): Promise<WorkerArtifactInput> {
  const contentType = file.type || contentTypeForFileName(file.name);
  const presignResponse = await fetch(`${API_BASE_URL}/api/submissions/presigned-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_name: file.name,
      content_type: contentType,
      kind,
    }),
  });

  if (!presignResponse.ok) {
    const failure = await presignResponse.json().catch(() => ({}));
    throw new Error(failure.detail || "Failed to create upload URL.");
  }

  const presign = (await presignResponse.json()) as {
    upload_url: string;
    object_key: string;
    headers: Record<string, string>;
  };

  const uploadResponse = await fetch(presign.upload_url, {
    method: "PUT",
    headers: presign.headers,
    body: file,
  });
  if (!uploadResponse.ok) {
    throw new Error("Upload to S3 failed.");
  }

  return {
    kind,
    object_key: presign.object_key,
    file_name: file.name,
    content_type: contentType,
    size_bytes: file.size,
  };
}

function buildWorkerRun({
  id,
  repoUrl,
  branch,
  status,
  activity,
  error,
  result,
  summary,
  startedAt,
}: {
  id: string;
  repoUrl: string;
  branch?: string | null;
  status: AnalysisRunState["status"];
  activity?: string;
  error?: string;
  result?: AnalyzeResponse;
  summary?: string;
  startedAt?: string;
}): AnalysisRunState {
  const now = new Date().toISOString();
  return {
    id,
    revision: 0,
    status,
    request: { repo_url: repoUrl, branch: branch || undefined },
    branch: branch || undefined,
    current_activity: activity,
    error,
    phases: [
      {
        id: "submission",
        title: "Submission",
        description: "Persist submitted project metadata and uploaded artifacts.",
        status: "completed",
        subtasks: [
          {
            id: "save_submission",
            title: "Save submission",
            description: "Store project metadata and uploaded artifact references.",
            status: "completed",
            badges: ["PostgreSQL"],
            activity_log: [],
          },
        ],
      },
      {
        id: "worker",
        title: "Worker Analysis",
        description: "Process the SQS analysis job and run enabled analyzers.",
        status: phaseStatusForRun(status),
        subtasks: [
          {
            id: "process_job",
            title: "Process job",
            description: activity || "Worker job is waiting for processing.",
            status: subtaskStatusForRun(status),
            detail: activity,
            badges: ["SQS", "S3", "Gemini"],
            activity_log: activity ? [activity] : [],
          },
        ],
      },
      {
        id: "feedback",
        title: "Feedback",
        description: "Persist final feedback scores and summaries.",
        status: status === "completed" ? "completed" : status === "failed" ? "failed" : "pending",
        subtasks: [
          {
            id: "save_feedback",
            title: "Save feedback",
            description: "Write final feedback to the database.",
            status: status === "completed" ? "completed" : status === "failed" ? "failed" : "pending",
            badges: ["PostgreSQL"],
            activity_log: [],
          },
        ],
      },
    ],
    events: [],
    result,
    markdown_report_content: summary,
    started_at: startedAt || now,
    updated_at: now,
    completed_at: status === "completed" || status === "failed" ? now : null,
  };
}

function activityForStatus(status: AnalysisRunState["status"]) {
  if (status === "queued") return "Queued for worker analysis";
  if (status === "running") return "Worker is analyzing submitted artifacts";
  if (status === "completed") return "Analysis completed";
  return "Analysis failed";
}

function phaseStatusForRun(status: AnalysisRunState["status"]) {
  if (status === "queued") return "pending";
  if (status === "running") return "in-progress";
  if (status === "completed") return "completed";
  return "failed";
}

function subtaskStatusForRun(status: AnalysisRunState["status"]) {
  if (status === "queued") return "pending";
  if (status === "running") return "in-progress";
  if (status === "completed") return "completed";
  return "failed";
}

function contentTypeForFileName(fileName: string) {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".mp4")) return "video/mp4";
  if (lower.endsWith(".webm")) return "video/webm";
  if (lower.endsWith(".mov")) return "video/quicktime";
  if (lower.endsWith(".mkv")) return "video/x-matroska";
  return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
}
