from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from src.github_agent.phase1.models.schemas import AnalyzeRequest, AnalyzeResponse


RunStatus = Literal["queued", "running", "completed", "failed"]
ItemStatus = Literal["pending", "in-progress", "completed", "failed", "skipped"]
RunEventKind = Literal[
    "info",
    "task-started",
    "task-completed",
    "agent-started",
    "agent-completed",
    "tool-started",
    "tool-finished",
    "llm-started",
    "reasoning-started",
    "reasoning-completed",
    "error",
]


class RunEventState(BaseModel):
    id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    phase_id: str | None = None
    subtask_id: str | None = None
    kind: RunEventKind = "info"
    message: str
    badges: list[str] = Field(default_factory=list)


class RunSubtaskState(BaseModel):
    id: str
    title: str
    description: str
    status: ItemStatus = "pending"
    detail: str | None = None
    badges: list[str] = Field(default_factory=list)
    activity_log: list[str] = Field(default_factory=list)


class RunPhaseState(BaseModel):
    id: str
    title: str
    description: str
    status: ItemStatus = "pending"
    subtasks: list[RunSubtaskState] = Field(default_factory=list)


class AnalysisRunState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    revision: int = 0
    status: RunStatus = "queued"
    request: AnalyzeRequest
    owner: str | None = None
    repo: str | None = None
    branch: str | None = None
    current_activity: str | None = None
    error: str | None = None
    phases: list[RunPhaseState] = Field(default_factory=list)
    events: list[RunEventState] = Field(default_factory=list)
    result: AnalyzeResponse | None = None
    markdown_report_content: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


def build_default_run_phases() -> list[RunPhaseState]:
    return [
        RunPhaseState(
            id="phase1",
            title="Phase 1: Repo Context Build",
            description="Collect repository metadata, tree structure, and documentation previews.",
            subtasks=[
                RunSubtaskState(id="parse_repo", title="Parse repository URL", description="Validate and parse the GitHub repository URL."),
                RunSubtaskState(id="fetch_metadata", title="Fetch GitHub metadata", description="Fetch repository metadata and resolve the target branch."),
                RunSubtaskState(id="fetch_tree", title="Fetch recursive tree", description="Load the repository tree for the target branch."),
                RunSubtaskState(id="filter_tree", title="Filter selected files", description="Filter the tree into a focused file set for analysis."),
                RunSubtaskState(id="fetch_docs", title="Fetch documentation previews", description="Fetch the top-level documentation files used as analysis evidence."),
                RunSubtaskState(id="save_context", title="Save repo context", description="Persist the Phase 1 artifact to repo_context.json."),
            ],
        ),
        RunPhaseState(
            id="phase2",
            title="Phase 2: Tree Analysis",
            description="Group files, resolve ambiguity, and derive specialist routing.",
            subtasks=[
                RunSubtaskState(id="task1_grouping", title="Task 1: Grouping", description="Classify files into component groups from tree-level evidence."),
                RunSubtaskState(id="task2_resolution", title="Task 2: Resolution", description="Resolve uncertain and unclassified files with bounded previews."),
                RunSubtaskState(id="build_tree_plan", title="Build tree analysis plan", description="Merge group outputs into the final tree analysis plan."),
                RunSubtaskState(id="derive_specialist_focus", title="Derive specialist focus", description="Assign grouped components to specialist reviewers."),
            ],
        ),
        RunPhaseState(
            id="phase3",
            title="Phase 3: Repository Analysis",
            description="Run specialist analysis passes and synthesize the final report.",
            subtasks=[
                RunSubtaskState(id="repo_intake", title="Repo Intake", description="Build a high-level understanding of the repository."),
                RunSubtaskState(id="frontend_review", title="Frontend Review", description="Analyze frontend structure and browser-side behavior."),
                RunSubtaskState(id="backend_review", title="Backend Review", description="Analyze backend, persistence, and worker behavior."),
                RunSubtaskState(id="integration_security_review", title="Integration & Security Review", description="Analyze integrations, config surfaces, and security-sensitive boundaries."),
                RunSubtaskState(id="platform_quality_review", title="Platform Quality Review", description="Evaluate tests, tooling, CI/CD, and engineering quality."),
                RunSubtaskState(id="final_report", title="Final Report", description="Synthesize specialist outputs into the final assessment."),
            ],
        ),
        RunPhaseState(
            id="outputs",
            title="Final Report Output",
            description="Persist the final JSON and markdown outputs for the run.",
            subtasks=[
                RunSubtaskState(id="save_repository_analysis", title="Save repository analysis", description="Persist repository_analysis.json."),
                RunSubtaskState(id="save_markdown_report", title="Save markdown report", description="Persist repository_report.md."),
            ],
        ),
    ]
