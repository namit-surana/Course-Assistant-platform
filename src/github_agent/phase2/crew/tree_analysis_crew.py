from __future__ import annotations

import json
import logging
from typing import Any
from typing import Callable

from pydantic import BaseModel, Field

from src.api_ui.services.crewai_live_events import bind_crewai_run_context
from src.github_agent.phase2.models.schemas import Task1GroupingOutput, Task2ResolutionOutput, TreeAnalysisInput
from src.utils.usage_metrics import format_usage_summary, summarize_usage


try:
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.project import CrewBase, agent, crew, task, tool
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("CrewAI is required for Phase 2 tree analysis. Install dependencies from requirements.txt.") from exc


logger = logging.getLogger(__name__)


class FilePreviewToolSchema(BaseModel):
    path: str = Field(description="Repository file path to inspect.")
    start_line: int = Field(default=1, ge=1, description="1-based line number to start reading from.")
    max_lines: int = Field(default=80, ge=1, le=200, description="Maximum number of lines to return.")


@CrewBase
class TreeAnalysisCrew:
    """Native CrewAI Phase 2 crew for repository structure analysis."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(
        self,
        model: str,
        preview_fetcher: Callable[[str, int, int], str] | None = None,
        progress_callback: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self.model = model
        self.preview_fetcher = preview_fetcher
        self.progress_callback = progress_callback
        self.allowed_review_paths: set[str] = set()
        self.seen_preview_chunks: set[tuple[str, int, int]] = set()

    @agent
    def tree_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["tree_analysis_agent"],
            llm=LLM(model=self.model),
            verbose=False,
            allow_delegation=False,
        )

    @task
    def task1_grouping(self) -> Task:
        return Task(
            config=self.tasks_config["task1_grouping"],
            output_json=Task1GroupingOutput,
            callback=self.capture_review_targets,
        )

    @task
    def task2_resolution(self) -> Task:
        return Task(
            config=self.tasks_config["task2_resolution"],
            output_json=Task2ResolutionOutput,
            callback=self.capture_task2_completion,
        )

    @tool
    def fetch_uncertain_file_preview(self) -> Any:
        try:
            from crewai.tools import BaseTool
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("CrewAI tool support is required for Phase 2 uncertainty resolution.") from exc

        outer_self = self

        class UncertainFilePreviewTool(BaseTool):
            name: str = "fetch_uncertain_file_preview"
            description: str = (
                "Fetch a bounded preview snippet for a file that Task 1 marked as uncertain or unclassified. "
                "Use this only for review-target file paths from Task 1. "
                "You may optionally provide start_line and max_lines to continue reading deeper in the file."
            )
            args_schema: type[BaseModel] = FilePreviewToolSchema

            def _run(self, path: str, start_line: int = 1, max_lines: int = 80) -> str:
                if path not in outer_self.allowed_review_paths:
                    return f"Preview access denied. {path} was not marked uncertain or unclassified by Task 1."
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
                if outer_self.progress_callback is not None:
                    outer_self.progress_callback(
                        "task2_resolution",
                        "in-progress",
                        f"Reviewing {path} lines {start_line}-{start_line + max_lines - 1}",
                    )
                return outer_self.preview_fetcher(path, start_line, max_lines)

        return UncertainFilePreviewTool()

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
            tracing=True,
        )

    def capture_review_targets(self, task_output: Any) -> None:
        payload: dict[str, Any] | None = None
        if getattr(task_output, "json_dict", None) is not None:
            payload = task_output.json_dict
        elif getattr(task_output, "pydantic", None) is not None:
            payload = task_output.pydantic.model_dump(mode="json")
        elif getattr(task_output, "raw", None):
            raw_output = task_output.raw
            if isinstance(raw_output, str):
                try:
                    payload = json.loads(raw_output)
                except json.JSONDecodeError:
                    payload = None

        if not isinstance(payload, dict):
            self.allowed_review_paths = set()
            return

        try:
            task1_output = Task1GroupingOutput.model_validate(payload)
        except Exception:  # noqa: BLE001
            self.allowed_review_paths = set()
            return

        self.allowed_review_paths = {item.path for item in task1_output.uncertain_files}
        self.allowed_review_paths.update(task1_output.unclassified_files)
        if self.progress_callback is not None:
            self.progress_callback("task1_grouping", "completed", "Task 1 grouping completed")
            self.progress_callback("task2_resolution", "in-progress", "Task 2 resolution started")

    def capture_task2_completion(self, _: Any) -> None:
        if self.progress_callback is not None:
            self.progress_callback("task2_resolution", "completed", "Task 2 resolution completed")


def run_tree_analysis_sequence(
    analysis_input: TreeAnalysisInput,
    model: str,
    preview_fetcher: Callable[[str, int, int], str] | None = None,
    progress_callback: Callable[[str, str, str], None] | None = None,
    run_reporter: Any | None = None,
) -> tuple[Any, Any]:
    crew_instance = TreeAnalysisCrew(
        model=model,
        preview_fetcher=preview_fetcher,
        progress_callback=progress_callback,
    )
    crew = crew_instance.crew()
    task1 = crew_instance.task1_grouping()
    task2 = crew_instance.task2_resolution()

    if progress_callback is not None:
        progress_callback("task1_grouping", "in-progress", "Task 1 grouping started")

    if run_reporter is None:
        crew.kickoff(
            inputs={"analysis_input_json": analysis_input.model_dump_json(indent=2)}
        )
    else:
        with bind_crewai_run_context(
            run_reporter,
            phase_id="phase2",
            task_name_map={
                "task1_grouping": "task1_grouping",
                "task2_resolution": "task2_resolution",
            },
        ):
            crew.kickoff(
                inputs={"analysis_input_json": analysis_input.model_dump_json(indent=2)}
            )
    _log_usage_metrics("Phase 2 tree analysis", model, crew)
    return task1.output, task2.output


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
