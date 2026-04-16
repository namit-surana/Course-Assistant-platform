from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.github_agent.phase1.models.schemas import DocumentationFile, RepoMetadata, TreeSummary


ComponentName = Literal[
    "overview_docs",
    "frontend",
    "backend",
    "database_schema",
    "workers",
    "integrations",
    "config_env",
    "build_dependencies",
    "infra_deployment",
    "tests",
    "tools_scripts",
    "data_assets_dataset",
]

SpecialistName = Literal[
    "frontend_agent",
    "backend_agent",
    "integration_security_agent",
    "platform_quality_agent",
]

RepoType = Literal[
    "backend_service",
    "frontend_app",
    "full_stack_app",
    "monorepo",
    "library",
    "infra_repo",
    "hybrid_tooling_repo",
]


class Phase1RepoContextInput(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    repo_metadata: RepoMetadata
    tree_summary: TreeSummary
    selected_files: list[str]
    filtered_out_files: list[str] = Field(default_factory=list)
    documentation_files: list[DocumentationFile] = Field(default_factory=list)
    created_at: datetime | None = None
    preview_content: dict[str, Any] | None = None


class TreeAnalysisInput(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    repo_metadata: RepoMetadata
    tree_summary: TreeSummary
    selected_files: list[str]
    documentation_previews: list[DocumentationFile] = Field(default_factory=list)
    guaranteed_coverage_metadata: dict[str, Any] | None = None


class UncertainFile(BaseModel):
    path: str
    candidate_groups: list[ComponentName]
    reason: str


class Task1GroupingOutput(BaseModel):
    repo_type: RepoType
    groups: dict[ComponentName, list[str]] = Field(default_factory=dict)
    uncertain_files: list[UncertainFile] = Field(default_factory=list)
    unclassified_files: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class Task2ResolutionOutput(BaseModel):
    resolved_groups: dict[ComponentName, list[str]] = Field(default_factory=dict)
    remaining_uncertain_files: list[UncertainFile] = Field(default_factory=list)
    remaining_unclassified_files: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class EntrypointCandidates(BaseModel):
    backend: list[str] = Field(default_factory=list)
    frontend: list[str] = Field(default_factory=list)


class SpecialistFocus(BaseModel):
    agent: SpecialistName
    groups: list[ComponentName] = Field(default_factory=list)
    assigned_paths: list[str] = Field(default_factory=list)
    reason: str


class TreeAnalysisPlan(BaseModel):
    repo_type: RepoType
    confidence: float | None = None
    important_paths: list[str] = Field(default_factory=list)
    entrypoint_candidates: EntrypointCandidates = Field(default_factory=EntrypointCandidates)
    groups: dict[ComponentName, list[str]] = Field(default_factory=dict)
    specialist_focus: list[SpecialistFocus] = Field(default_factory=list)
    fetch_priority: list[str] = Field(default_factory=list)
    remaining_uncertain_files: list[UncertainFile] = Field(default_factory=list)
    unclassified_files: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class TreeAnalysisOutputFile(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    source_repo_context_file: str
    analysis_input: TreeAnalysisInput
    task1_output: Task1GroupingOutput
    task2_output: Task2ResolutionOutput
    plan: TreeAnalysisPlan
    created_at: datetime

    model_config = ConfigDict(json_encoders={Path: str})
