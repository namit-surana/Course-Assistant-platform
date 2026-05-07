import type {
  AnalysisRunState,
  AnalyzeResponse,
  ItemStatus,
  RunPhaseState,
  RubricCriterionInput,
  WorkerArtifactInput,
  WorkerSubmissionDetail,
  WorkerSubmissionResponse,
  WorkerVideoAnalysisJob,
  WorkerVideoAnalysisStartResponse,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const mapJobStatus = (status: "queued" | "running" | "completed" | "failed") => status;

type SubmissionAnalysisStartApiResponse = {
  submission_id: string;
  job_id: string;
  job_type:
    | "submission_analysis"
    | "git_analysis"
    | "ppt_analysis"
    | "video_analysis"
    | "final_grading_analysis";
  status: "queued" | "running" | "completed" | "failed";
  queued: boolean;
  sqs_message_id?: string | null;
};

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

  const response = await fetch(`${API_BASE_URL}/api/v1/submissions`, {
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

  // 🔥 FIX: proper error parsing
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(
      typeof failure.detail === "string"
        ? failure.detail
        : JSON.stringify(failure.detail, null, 2)
    );
  }

  const submission = (await response.json()) as WorkerSubmissionResponse;

  return {
    submission,
    run: buildWorkerRun({
      id: submission.id,
      repoUrl,
      branch,
      status: submission.status,
      activity: submission.queued
        ? "Queued for worker analysis"
        : "Submission saved. Waiting for organizer to start processing.",
    }),
  };
}

export async function startWorkerSubmissionProcessing({
  submissionId,
}: {
  submissionId: string;
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}/processing/start`, {
    method: "POST",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start processing.");
  }
  const started = (await response.json()) as {
    submission_id: string;
    job_id: string;
    job_type:
      | "submission_analysis"
      | "git_analysis"
      | "ppt_analysis"
      | "video_analysis"
      | "final_grading_analysis";
    status: "queued" | "running" | "completed" | "failed";
    queued: boolean;
    sqs_message_id?: string | null;
  };
  return { ...started, status: mapJobStatus(started.status) };
}

export async function fetchWorkerSubmission(
  submissionId: string
): Promise<WorkerSubmissionDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}`);

  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(
      typeof failure.detail === "string"
        ? failure.detail
        : JSON.stringify(failure.detail, null, 2)
    );
  }

  return (await response.json()) as WorkerSubmissionDetail;
}

export async function startWorkerSubmissionVideoAnalysis({
  submissionId,
}: {
  submissionId: string;
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}/video-analysis/start`, {
    method: "POST",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start video analysis.");
  }
  const started = (await response.json()) as SubmissionAnalysisStartApiResponse;
  return {
    ...started,
    status: mapJobStatus(started.status),
  };
}

export async function startWorkerSubmissionPptAnalysis({
  submissionId,
}: {
  submissionId: string;
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}/ppt-analysis/start`, {
    method: "POST",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start presentation analysis.");
  }
  const started = (await response.json()) as SubmissionAnalysisStartApiResponse;
  return {
    ...started,
    status: mapJobStatus(started.status),
  };
}

export async function startWorkerSubmissionGitAnalysis({
  submissionId,
}: {
  submissionId: string;
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}/git-analysis/start`, {
    method: "POST",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start repository analysis.");
  }
  const started = (await response.json()) as SubmissionAnalysisStartApiResponse;
  return {
    ...started,
    status: mapJobStatus(started.status),
  };
}

export async function startWorkerSubmissionFinalGrading({
  submissionId,
}: {
  submissionId: string;
}): Promise<WorkerVideoAnalysisStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions/${submissionId}/final-grading/start`, {
    method: "POST",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to start final grading.");
  }
  const started = (await response.json()) as SubmissionAnalysisStartApiResponse;
  return {
    ...started,
    status: mapJobStatus(started.status),
  };
}

export async function fetchWorkerVideoAnalysisJob(jobId: string): Promise<WorkerVideoAnalysisJob> {
  const response = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.detail || "Unable to load video analysis job.");
  }
  const job = (await response.json()) as {
    job_id: string;
    submission_id: string;
    job_type:
      | "submission_analysis"
      | "git_analysis"
      | "ppt_analysis"
      | "video_analysis"
      | "final_grading_analysis";
    status: "queued" | "running" | "completed" | "failed";
    attempts: number;
    error?: string | null;
    created_at: string;
    updated_at: string;
  };
  return {
    job_id: job.job_id,
    submission_id: job.submission_id,
    job_type: job.job_type,
    status: mapJobStatus(job.status),
    attempts: job.attempts,
    error: job.error ?? null,
    created_at: job.created_at,
    updated_at: job.updated_at,
    raw_output: null,
    parsed: null,
  };
}

export function mapWorkerSubmissionToRun(
  detail: WorkerSubmissionDetail,
  previousRun: AnalysisRunState
): AnalysisRunState {
  const repositoryResult = detail.feedback?.raw_result?.repository;
  const repositoryHasFindings = Boolean(repositoryResult?.repository_analysis);
  const repositoryError = repositoryResult?.error;
  const effectiveStatus =
    detail.status === "completed" && repositoryError && !repositoryHasFindings
      ? "failed"
      : detail.status;

  const fallbackResult: AnalyzeResponse | undefined = repositoryHasFindings
    ? repositoryResult
    : undefined;

  return buildWorkerRun({
    id: previousRun.id,
    repoUrl: detail.repo_url || previousRun.request.repo_url,
    branch: detail.branch || previousRun.request.branch,
    status: effectiveStatus,
    error: detail.error_message || repositoryError || undefined,
    activity: activityForStatus(effectiveStatus),
    result: fallbackResult,
    summary: detail.feedback?.summary || undefined,
    startedAt: previousRun.started_at,
  });
}

async function uploadArtifact(
  file: File,
  kind: WorkerArtifactInput["kind"]
): Promise<WorkerArtifactInput> {
  const contentType = file.type || contentTypeForFileName(file.name);

  const presignResponse = await fetch(`${API_BASE_URL}/api/v1/submissions/presigned-url`, {
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
    throw new Error(
      typeof failure.detail === "string"
        ? failure.detail
        : JSON.stringify(failure.detail, null, 2)
    );
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
    phases: buildWorkerPhases(status),
    events: [],
    result,
    markdown_report_content: summary,
    started_at: startedAt || now,
    updated_at: now,
    completed_at:
      status === "completed" || status === "failed" ? now : null,
  };
}

function buildWorkerPhases(status: AnalysisRunState["status"]): RunPhaseState[] {
  const phaseStatus = (index: number): ItemStatus => {
    if (status === "submitted") return "pending";
    if (status === "queued") return index === 0 ? "in-progress" : "pending";
    if (status === "running") return index < 2 ? "completed" : index === 2 ? "in-progress" : "pending";
    if (status === "completed") return "completed";
    if (status === "failed") return index === 0 ? "failed" : "pending";
    return "pending";
  };

  return [
    {
      id: "queued",
      title: "Queued",
      description: "Analysis job is waiting for the worker.",
      status: phaseStatus(0),
      subtasks: [],
    },
    {
      id: "fetch",
      title: "Fetch Inputs",
      description: "Load submitted repository and artifact inputs.",
      status: phaseStatus(1),
      subtasks: [],
    },
    {
      id: "analyze",
      title: "Analyze",
      description: "Run repository, presentation, and video analyzers as applicable.",
      status: phaseStatus(2),
      subtasks: [],
    },
    {
      id: "save",
      title: "Save Results",
      description: "Persist final feedback for the dashboard.",
      status: phaseStatus(3),
      subtasks: [],
    },
  ];
}

function activityForStatus(status: AnalysisRunState["status"]) {
  if (status === "submitted") return "Submission saved; waiting for organizer to start processing";
  if (status === "queued") return "Queued for worker analysis";
  if (status === "running") return "Processing…";
  if (status === "completed") return "Analysis completed";
  return "Analysis failed";
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
