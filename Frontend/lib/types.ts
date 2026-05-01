// ── EvalAI product types ──────────────────────────────────────────────────────

export type EventStatus = "active" | "draft" | "completed";
export type EventType = "hackathon" | "course" | "custom";
export type ArtifactStatus = "submitted" | "pending" | "missing";

export interface EvalEvent {
  id: string;
  name: string;
  type: EventType;
  status: EventStatus;
  teamsTotal: number;
  teamsEvaluated: number;
  submissionDeadline: string;
  judgingDeadline: string;
  createdAt: string;
}

export interface ActivityItem {
  id: string;
  type: "analysis_complete" | "submission" | "judge_action" | "event_created" | "result_published";
  description: string;
  meta: string;
  time: string;
}

export interface StatCard {
  label: string;
  value: string | number;
  sub: string;
  trend?: "up" | "down" | "neutral";
}

// ── Repository analyzer types (from analyze workspace) ────────────────────────

export type RunStatus = "queued" | "running" | "completed" | "failed";
export type ItemStatus =
  | "pending"
  | "in-progress"
  | "completed"
  | "failed"
  | "skipped";

export interface RunSubtaskState {
  id: string;
  title: string;
  description: string;
  status: ItemStatus;
  detail?: string | null;
  badges: string[];
  activity_log: string[];
}

export interface RunPhaseState {
  id: string;
  title: string;
  description: string;
  status: ItemStatus;
  subtasks: RunSubtaskState[];
}

export interface RunEventState {
  id: number;
  timestamp: string;
  phase_id?: string | null;
  subtask_id?: string | null;
  kind: string;
  message: string;
  badges: string[];
}

export interface AnalyzeResponse {
  status: string;
  repo_url: string;
  owner: string;
  repo: string;
  branch: string;
  tree_analysis_plan?: {
    groups?: Record<string, string[]>;
  };
  repository_analysis?: {
    report_title?: string;
    executive_summary?: string;
    repository_overview?: string;
    component_summary?: string[];
    runtime_behavior?: string[];
    architecture_patterns?: string[];
    risks_and_weaknesses?: string[];
    quality_assessment?: string;
    strengths?: string[];
    intelligent_questions?: string[];
    recommended_next_steps?: string[];
    evidence_paths?: string[];
  };
  markdown_report_file?: string;
  repo_chunk_index_file?: string;
}

export interface AnalysisRunState {
  id: string;
  revision: number;
  status: RunStatus;
  request: CreateRunPayload;
  owner?: string | null;
  repo?: string | null;
  branch?: string | null;
  current_activity?: string | null;
  error?: string | null;
  phases: RunPhaseState[];
  events: RunEventState[];
  result?: AnalyzeResponse | null;
  markdown_report_content?: string | null;
  started_at?: string;
  updated_at?: string;
  completed_at?: string | null;
}

export interface CreateRunPayload {
  repo_url: string;
  branch?: string;
}

export interface PlanSubtask {
  id: string;
  title: string;
  description: string;
  status: ItemStatus;
  tools?: string[];
  activity?: string[];
}

export interface PlanTask {
  id: string;
  title: string;
  description: string;
  status: ItemStatus;
  dependencies: string[];
  subtasks: PlanSubtask[];
}

// ── EvalAI submission types ───────────────────────────────────────────────────

export type VoiceStatus = "idle" | "recording" | "processing" | "completed" | "failed";

export interface VoiceTranscriptSegment {
  text: string;
  start?: number | null;
  end?: number | null;
}

export interface VoiceTranscriptArtifact {
  session_id: string;
  event_id?: string | null;
  submission_id?: string | null;
  full_transcript: string;
  segments: VoiceTranscriptSegment[];
  provider: string;
  model: string;
  created_at: string;
  output_file?: string | null;
}

export interface Submission {
  id: string;
  eventId: string;
  teamName: string;
  repoUrl: string;
  branch?: string;
  runId: string;
  run: AnalysisRunState;
  voiceStatus?: VoiceStatus;
  voiceTranscript?: VoiceTranscriptArtifact | null;
  createdAt: string;
}
