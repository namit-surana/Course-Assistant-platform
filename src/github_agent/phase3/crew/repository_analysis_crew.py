from __future__ import annotations

import logging
from typing import Any
from typing import Callable

from pydantic import BaseModel, Field

from src.api_ui.services.crewai_live_events import bind_crewai_run_context
from src.api_ui.services.run_store import RunProgressReporter
from src.github_agent.phase3.models.schemas import (
    FinalRepositoryAnalysis,
    RepoIntakeOutput,
    RepositoryAnalysisInput,
    SpecialistAnalysisOutput,
    SpecialistSynthesisSummary,
    SpecialistPromptInput,
)
from src.utils.usage_metrics import format_usage_summary, summarize_usage


try:
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.project import CrewBase, agent, crew, task, tool
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("CrewAI is required for Phase 3 repository analysis. Install dependencies from requirements.txt.") from exc


logger = logging.getLogger(__name__)


class RepoFilePreviewToolSchema(BaseModel):
    path: str = Field(description="Repository file path to inspect.")
    start_line: int = Field(default=1, ge=1, description="1-based line number to start reading from.")
    max_lines: int = Field(default=80, ge=1, le=200, description="Maximum number of lines to return.")


@CrewBase
class RepositoryAnalysisStepCrew:
    """CrewAI-native single-step repository analysis crew used by Phase 3 flow methods."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        model: str,
        analysis_input: RepositoryAnalysisInput,
        selected_task_names: tuple[str, ...],
        preview_fetcher: Callable[[str, int, int], str] | None = None,
        allowed_preview_paths: set[str] | None = None,
        enable_tracing: bool = True,
    ) -> None:
        self.model = model
        self.analysis_input = analysis_input
        self.selected_task_names = set(selected_task_names)
        self.preview_fetcher = preview_fetcher
        preview_scope = analysis_input.selected_files if allowed_preview_paths is None else allowed_preview_paths
        self.allowed_preview_paths = set(preview_scope)
        self.enable_tracing = enable_tracing
        self.seen_preview_chunks: set[tuple[str, int, int]] = set()

    @agent
    def repo_intake_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["repo_intake_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @agent
    def frontend_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["frontend_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @agent
    def backend_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["backend_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @agent
    def integration_security_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["integration_security_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @agent
    def platform_quality_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["platform_quality_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @task
    def repo_intake_task(self) -> Task:
        return Task(
            name="01_repo_intake",
            config=self.tasks_config["repo_intake_task"],
            output_pydantic=RepoIntakeOutput,
        )

    @task
    def frontend_analysis_task(self) -> Task:
        return Task(
            name="02_frontend_review",
            config=self.tasks_config["frontend_analysis_task"],
            output_pydantic=SpecialistAnalysisOutput,
        )

    @task
    def backend_analysis_task(self) -> Task:
        return Task(
            name="03_backend_review",
            config=self.tasks_config["backend_analysis_task"],
            output_pydantic=SpecialistAnalysisOutput,
        )

    @task
    def integration_security_task(self) -> Task:
        return Task(
            name="04_integration_security_review",
            config=self.tasks_config["integration_security_task"],
            output_pydantic=SpecialistAnalysisOutput,
        )

    @task
    def platform_quality_task(self) -> Task:
        return Task(
            name="05_platform_quality_review",
            config=self.tasks_config["platform_quality_task"],
            output_pydantic=SpecialistAnalysisOutput,
        )

    @task
    def final_report_task(self) -> Task:
        return Task(
            name="06_final_report",
            config=self.tasks_config["final_report_task"],
            output_pydantic=FinalRepositoryAnalysis,
        )

    @tool
    def fetch_repo_file_preview(self) -> Any:
        try:
            from crewai.tools import BaseTool
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("CrewAI tool support is required for final repository analysis.") from exc

        outer_self = self

        class RepoFilePreviewTool(BaseTool):
            name: str = "fetch_repo_file_preview"
            description: str = (
                "Fetch a bounded text preview for a repository file that appears in the selected file set. "
                "Use this to inspect only the most relevant evidence files before drawing conclusions. "
                "You may optionally provide start_line and max_lines to continue reading deeper in a file."
            )
            args_schema: type[BaseModel] = RepoFilePreviewToolSchema

            def _run(self, path: str, start_line: int = 1, max_lines: int = 80) -> str:
                if path not in outer_self.allowed_preview_paths:
                    return f"Preview access denied. {path} was not included in the selected file set."
                if outer_self.preview_fetcher is None:
                    return f"Preview fetcher unavailable for {path}."
                chunk_key = (path, start_line, max_lines)
                if chunk_key in outer_self.seen_preview_chunks:
                    end_line = start_line + max_lines - 1
                    return (
                        f"Chunk already fetched for {path} lines {start_line}-{end_line}. "
                        "Use the evidence you already have, or request a different line range only if a specific "
                        "unresolved question remains."
                    )
                outer_self.seen_preview_chunks.add(chunk_key)
                return outer_self.preview_fetcher(path, start_line, max_lines)

        return RepoFilePreviewTool()

    @crew
    def crew(self) -> Crew:
        selected_tasks = [task for task in self.tasks if task.name in self.selected_task_names]
        selected_roles = {task.agent.role for task in selected_tasks if getattr(task, "agent", None) is not None}
        selected_agents = [agent for agent in self.agents if agent.role in selected_roles]
        return Crew(
            agents=selected_agents,
            tasks=selected_tasks,
            process=Process.sequential,
            verbose=False,
            tracing=self.enable_tracing,
        )


def _require_model(task_output: Any, model_type: type[Any], task_name: str) -> Any:
    if getattr(task_output, "pydantic", None) is not None:
        return task_output.pydantic
    if getattr(task_output, "json_dict", None) is not None:
        return model_type.model_validate(task_output.json_dict)
    if getattr(task_output, "raw", None):
        return model_type.model_validate_json(task_output.raw)
    raise RuntimeError(f"{task_name} did not produce structured output.")


def _run_single_task(
    *,
    analysis_input: RepositoryAnalysisInput,
    model: str,
    task_method_name: str,
    selected_task_name: str,
    run_subtask_id: str,
    model_type: type[Any],
    inputs: dict[str, str],
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    allowed_preview_paths: set[str] | None = None,
    run_reporter: RunProgressReporter | None = None,
    enable_tracing: bool = True,
) -> Any:
    crew_instance = RepositoryAnalysisStepCrew(
        model=model,
        analysis_input=analysis_input,
        selected_task_names=(selected_task_name,),
        preview_fetcher=preview_fetcher,
        allowed_preview_paths=allowed_preview_paths,
        enable_tracing=enable_tracing,
    )
    crew = crew_instance.crew()
    task_instance = getattr(crew_instance, task_method_name)()
    if run_reporter is None:
        crew.kickoff(inputs=inputs)
    else:
        with bind_crewai_run_context(
            run_reporter,
            phase_id="phase3",
            default_subtask_id=run_subtask_id,
            task_name_map={selected_task_name: run_subtask_id},
        ):
            crew.kickoff(inputs=inputs)
    _log_usage_metrics(task_method_name, model, crew)
    return _require_model(task_instance.output, model_type, task_method_name)


def run_repo_intake_analysis(
    analysis_input: RepositoryAnalysisInput,
    model: str,
    run_reporter: RunProgressReporter | None = None,
) -> RepoIntakeOutput:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="repo_intake_task",
        selected_task_name="01_repo_intake",
        run_subtask_id="repo_intake",
        model_type=RepoIntakeOutput,
        inputs={"analysis_input_json": analysis_input.model_dump_json(indent=2)},
        run_reporter=run_reporter,
    )


def run_frontend_review(
    analysis_input: RepositoryAnalysisInput,
    specialist_input: SpecialistPromptInput,
    model: str,
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    run_reporter: RunProgressReporter | None = None,
) -> SpecialistAnalysisOutput:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="frontend_analysis_task",
        selected_task_name="02_frontend_review",
        run_subtask_id="frontend_review",
        model_type=SpecialistAnalysisOutput,
        inputs={
            "specialist_input_json": specialist_input.model_dump_json(indent=2),
        },
        preview_fetcher=preview_fetcher,
        allowed_preview_paths=set(specialist_input.assigned_paths),
        run_reporter=run_reporter,
        enable_tracing=False,
    )


def run_backend_review(
    analysis_input: RepositoryAnalysisInput,
    specialist_input: SpecialistPromptInput,
    model: str,
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    run_reporter: RunProgressReporter | None = None,
) -> SpecialistAnalysisOutput:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="backend_analysis_task",
        selected_task_name="03_backend_review",
        run_subtask_id="backend_review",
        model_type=SpecialistAnalysisOutput,
        inputs={
            "specialist_input_json": specialist_input.model_dump_json(indent=2),
        },
        preview_fetcher=preview_fetcher,
        allowed_preview_paths=set(specialist_input.assigned_paths),
        run_reporter=run_reporter,
        enable_tracing=False,
    )


def run_integration_security_review(
    analysis_input: RepositoryAnalysisInput,
    specialist_input: SpecialistPromptInput,
    model: str,
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    run_reporter: RunProgressReporter | None = None,
) -> SpecialistAnalysisOutput:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="integration_security_task",
        selected_task_name="04_integration_security_review",
        run_subtask_id="integration_security_review",
        model_type=SpecialistAnalysisOutput,
        inputs={
            "specialist_input_json": specialist_input.model_dump_json(indent=2),
        },
        preview_fetcher=preview_fetcher,
        allowed_preview_paths=set(specialist_input.assigned_paths),
        run_reporter=run_reporter,
        enable_tracing=False,
    )


def run_platform_quality_review(
    analysis_input: RepositoryAnalysisInput,
    specialist_input: SpecialistPromptInput,
    model: str,
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    run_reporter: RunProgressReporter | None = None,
) -> SpecialistAnalysisOutput:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="platform_quality_task",
        selected_task_name="05_platform_quality_review",
        run_subtask_id="platform_quality_review",
        model_type=SpecialistAnalysisOutput,
        inputs={
            "specialist_input_json": specialist_input.model_dump_json(indent=2),
        },
        preview_fetcher=preview_fetcher,
        allowed_preview_paths=set(specialist_input.assigned_paths),
        run_reporter=run_reporter,
        enable_tracing=False,
    )


def run_final_report(
    analysis_input: RepositoryAnalysisInput,
    repo_intake_output: RepoIntakeOutput,
    frontend_summary: SpecialistSynthesisSummary,
    backend_summary: SpecialistSynthesisSummary,
    integration_security_summary: SpecialistSynthesisSummary,
    platform_quality_summary: SpecialistSynthesisSummary,
    model: str,
    run_reporter: RunProgressReporter | None = None,
) -> FinalRepositoryAnalysis:
    return _run_single_task(
        analysis_input=analysis_input,
        model=model,
        task_method_name="final_report_task",
        selected_task_name="06_final_report",
        run_subtask_id="final_report",
        model_type=FinalRepositoryAnalysis,
        inputs={
            "analysis_input_json": analysis_input.model_dump_json(indent=2),
            "repo_intake_json": repo_intake_output.model_dump_json(indent=2),
            "frontend_summary_json": frontend_summary.model_dump_json(indent=2),
            "backend_summary_json": backend_summary.model_dump_json(indent=2),
            "integration_security_summary_json": integration_security_summary.model_dump_json(indent=2),
            "platform_quality_summary_json": platform_quality_summary.model_dump_json(indent=2),
        },
        run_reporter=run_reporter,
    )


def _log_usage_metrics(label: str, model: str, crew: Any) -> None:
    usage_metrics = getattr(crew, "usage_metrics", None)
    if usage_metrics is None:
        logger.info("%s usage metrics unavailable", label)
        return
    summary = summarize_usage(label, model, usage_metrics)
    if summary is None:
        logger.info("%s usage metrics unavailable", label)
        return
    logger.info(format_usage_summary(summary))
