from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.github_agent.phase1.models.schemas import DocumentationFile, RepoMetadata, TreeSummary
from src.github_agent.phase2.models.schemas import ComponentName, EntrypointCandidates, RepoType, TreeAnalysisPlan


class RepositoryAnalysisInput(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    repo_metadata: RepoMetadata
    tree_summary: TreeSummary
    selected_files: list[str]
    documentation_previews: list[DocumentationFile] = Field(default_factory=list)
    tree_analysis_plan: TreeAnalysisPlan


class RepoIntakeOutput(BaseModel):
    repo_summary: str
    main_capabilities: list[str] = Field(default_factory=list)
    stack_summary: list[str] = Field(default_factory=list)
    maturity_signals: list[str] = Field(default_factory=list)
    architecture_hypotheses: list[str] = Field(default_factory=list)
    has_frontend: bool = False
    has_backend: bool = False
    has_integrations: bool = False
    has_platform_surface: bool = False
    focus_paths: list[str] = Field(default_factory=list)


class SpecialistPromptInput(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    repo_type: RepoType
    repo_summary: str
    stack_summary: list[str] = Field(default_factory=list)
    architecture_hypotheses: list[str] = Field(default_factory=list)
    important_paths: list[str] = Field(default_factory=list)
    entrypoint_candidates: EntrypointCandidates = Field(default_factory=EntrypointCandidates)
    focus_groups: list[ComponentName] = Field(default_factory=list)
    assigned_paths: list[str] = Field(default_factory=list)
    focus_reason: str


class SpecialistAnalysisOutput(BaseModel):
    applicable: bool
    summary: str
    runtime_behavior: list[str] = Field(default_factory=list)
    architecture_patterns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    intelligent_questions: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)


class SpecialistSynthesisSummary(BaseModel):
    applicable: bool
    summary: str
    top_runtime_behavior: list[str] = Field(default_factory=list)
    top_architecture_patterns: list[str] = Field(default_factory=list)
    top_risks: list[str] = Field(default_factory=list)
    top_strengths: list[str] = Field(default_factory=list)
    top_questions: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)


class FinalRepositoryAnalysis(BaseModel):
    report_title: str
    executive_summary: str
    repository_overview: str
    component_summary: list[str] = Field(default_factory=list)
    runtime_behavior: list[str] = Field(default_factory=list)
    architecture_patterns: list[str] = Field(default_factory=list)
    risks_and_weaknesses: list[str] = Field(default_factory=list)
    quality_assessment: str
    strengths: list[str] = Field(default_factory=list)
    intelligent_questions: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    evidence_paths: list[str] = Field(default_factory=list)


class RepositoryAnalysisRunResult(BaseModel):
    intake_output: RepoIntakeOutput
    frontend_output: SpecialistAnalysisOutput
    backend_output: SpecialistAnalysisOutput
    integration_security_output: SpecialistAnalysisOutput
    platform_quality_output: SpecialistAnalysisOutput
    final_analysis: FinalRepositoryAnalysis


class RepositoryAnalysisOutputFile(BaseModel):
    repo_url: str
    owner: str
    repo: str
    branch: str
    source_repo_context_file: str
    source_tree_analysis_file: str
    analysis_input: RepositoryAnalysisInput
    intake_output: RepoIntakeOutput
    frontend_output: SpecialistAnalysisOutput
    backend_output: SpecialistAnalysisOutput
    integration_security_output: SpecialistAnalysisOutput
    platform_quality_output: SpecialistAnalysisOutput
    final_analysis: FinalRepositoryAnalysis
    markdown_report_file: str
    created_at: datetime

    model_config = ConfigDict(json_encoders={Path: str})
