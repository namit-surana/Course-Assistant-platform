from __future__ import annotations

import asyncio
import logging
from pathlib import PurePosixPath

from src.api_ui.models.schemas import AnalysisRunState
from src.api_ui.services.run_store import AnalysisRunStore, RunNotFoundError, RunProgressReporter
from src.github_agent.phase1.models.schemas import AnalyzeRequest, AnalyzeResponse
from src.github_agent.phase1.services.context_builder import ContextBuilder
from src.github_agent.phase1.services.filter_service import FilterService
from src.github_agent.phase1.services.github_service import GitHubService
from src.github_agent.phase2.services.tree_analysis_service import TreeAnalysisService
from src.github_agent.phase3.services.repository_analysis_service import RepositoryAnalysisService
from src.utils.usage_metrics import format_usage_totals, usage_tracking_context


DOCUMENTATION_EXTENSIONS = {".md", ".mdx", ".rst", ".txt"}
logger = logging.getLogger(__name__)


class AnalysisRunService:
    """Coordinates live UI runs and inline analysis execution."""

    def __init__(self, store: AnalysisRunStore) -> None:
        self.store = store
        self._background_tasks: dict[str, asyncio.Task[None]] = {}

    async def start_run(
        self,
        request: AnalyzeRequest,
        *,
        github_service: GitHubService,
        filter_service: FilterService,
        context_builder: ContextBuilder,
        tree_analysis_service: TreeAnalysisService,
        repository_analysis_service: RepositoryAnalysisService,
    ) -> AnalysisRunState:
        run = self.store.create_run(request)
        reporter = RunProgressReporter(self.store, run.id)
        task = asyncio.create_task(
            self._execute_background(
                request=request,
                reporter=reporter,
                github_service=github_service,
                filter_service=filter_service,
                context_builder=context_builder,
                tree_analysis_service=tree_analysis_service,
                repository_analysis_service=repository_analysis_service,
            )
        )
        self._background_tasks[run.id] = task
        task.add_done_callback(lambda _: self._background_tasks.pop(run.id, None))
        return self.store.get_run(run.id)

    def get_run(self, run_id: str) -> AnalysisRunState:
        return self.store.get_run(run_id)

    async def run_inline(
        self,
        request: AnalyzeRequest,
        *,
        github_service: GitHubService,
        filter_service: FilterService,
        context_builder: ContextBuilder,
        tree_analysis_service: TreeAnalysisService,
        repository_analysis_service: RepositoryAnalysisService,
    ) -> AnalyzeResponse:
        return await self._execute_pipeline(
            request=request,
            reporter=None,
            github_service=github_service,
            filter_service=filter_service,
            context_builder=context_builder,
            tree_analysis_service=tree_analysis_service,
            repository_analysis_service=repository_analysis_service,
        )

    async def _execute_background(
        self,
        *,
        request: AnalyzeRequest,
        reporter: RunProgressReporter,
        github_service: GitHubService,
        filter_service: FilterService,
        context_builder: ContextBuilder,
        tree_analysis_service: TreeAnalysisService,
        repository_analysis_service: RepositoryAnalysisService,
    ) -> None:
        try:
            reporter.start()
            result = await self._execute_pipeline(
                request=request,
                reporter=reporter,
                github_service=github_service,
                filter_service=filter_service,
                context_builder=context_builder,
                tree_analysis_service=tree_analysis_service,
                repository_analysis_service=repository_analysis_service,
            )
            markdown_content = None
            if result.markdown_report_file:
                markdown_path = context_builder.output_dir / PurePosixPath(result.markdown_report_file).name
                if markdown_path.exists():
                    markdown_content = markdown_path.read_text(encoding="utf-8")
            reporter.complete_run(result, markdown_content)
        except Exception as exc:  # noqa: BLE001
            reporter.fail_run(str(exc))

    async def _execute_pipeline(
        self,
        *,
        request: AnalyzeRequest,
        reporter: RunProgressReporter | None,
        github_service: GitHubService,
        filter_service: FilterService,
        context_builder: ContextBuilder,
        tree_analysis_service: TreeAnalysisService,
        repository_analysis_service: RepositoryAnalysisService,
    ) -> AnalyzeResponse:
        repo_url = str(request.repo_url)
        with usage_tracking_context() as usage_totals:
            self._mark(reporter, "phase1", "parse_repo", "in-progress", "Parsing repository URL")
            repo_ref = github_service.parse_github_url(repo_url)
            self._mark(reporter, "phase1", "parse_repo", "completed", "Repository URL parsed")

            self._mark(reporter, "phase1", "fetch_metadata", "in-progress", "Fetching GitHub metadata")
            metadata = await github_service.get_repo_metadata(repo_ref.owner, repo_ref.repo)
            branch = request.branch or metadata.default_branch
            if reporter is not None:
                reporter.repo_details(repo_ref.owner, repo_ref.repo, branch)
            self._mark(reporter, "phase1", "fetch_metadata", "completed", f"Resolved target branch: {branch}")

            self._mark(reporter, "phase1", "fetch_tree", "in-progress", "Fetching repository tree")
            tree_items = await github_service.get_recursive_tree(repo_ref.owner, repo_ref.repo, branch)
            self._mark(reporter, "phase1", "fetch_tree", "completed", f"Loaded {len(tree_items)} tree items")

            self._mark(reporter, "phase1", "filter_tree", "in-progress", "Filtering selected files")
            filtered_context = filter_service.filter_tree(tree_items)
            self._mark(
                reporter,
                "phase1",
                "filter_tree",
                "completed",
                f"Selected {len(filtered_context.selected_paths)} files for analysis",
            )

            self._mark(reporter, "phase1", "fetch_docs", "in-progress", "Fetching documentation previews")
            documentation_paths = self._get_documentation_paths(filtered_context.selected_paths)
            documentation_files = [
                await github_service.get_file_content(repo_ref.owner, repo_ref.repo, branch, path)
                for path in documentation_paths
            ]
            self._mark(
                reporter,
                "phase1",
                "fetch_docs",
                "completed",
                f"Fetched {len(documentation_files)} documentation previews",
            )

            self._mark(reporter, "phase1", "save_context", "in-progress", "Saving repo context artifact")
            artifact = context_builder.build_context(
                repo_url=repo_url,
                owner=repo_ref.owner,
                repo=repo_ref.repo,
                branch=branch,
                repo_metadata=metadata,
                tree_items=tree_items,
                filtered_context=filtered_context,
                documentation_files=documentation_files,
            )
            output_path = context_builder.save_context(artifact)
            selected_file_documents = await asyncio.gather(
                *[
                    github_service.get_file_content(repo_ref.owner, repo_ref.repo, branch, path)
                    for path in filtered_context.selected_paths
                ]
            )
            chunk_index_artifact = context_builder.build_chunk_index(
                repo_url=repo_url,
                owner=repo_ref.owner,
                repo=repo_ref.repo,
                branch=branch,
                selected_files=selected_file_documents,
            )
            repo_chunk_index_path = context_builder.save_chunk_index(chunk_index_artifact)
            self._mark(
                reporter,
                "phase1",
                "save_context",
                "completed",
                "Saved repo_context.json and repo_chunk_index.json",
            )

            tree_analysis_plan, tree_analysis_output_path = await tree_analysis_service.run_phase2_from_file_with_output(
                output_path.as_posix(),
                progress_callback=self._phase_progress_callback(reporter, "phase2"),
                run_reporter=reporter,
            )

            repository_analysis, repository_analysis_output_path, markdown_report_path = (
                await repository_analysis_service.run_phase3_from_files_with_output(
                    output_path.as_posix(),
                    tree_analysis_output_path.as_posix(),
                    progress_callback=self._phase_progress_callback(reporter, "phase3"),
                    run_reporter=reporter,
                )
            )

            self._mark(
                reporter,
                "outputs",
                "save_repository_analysis",
                "completed",
                "Saved repository_analysis.json",
            )
            self._mark(
                reporter,
                "outputs",
                "save_markdown_report",
                "completed",
                "Saved repository_report.md",
            )

            logger.info(format_usage_totals("Repository analysis total usage", usage_totals))

            return AnalyzeResponse(
                status="success",
                repo_url=repo_url,
                owner=repo_ref.owner,
                repo=repo_ref.repo,
                branch=branch,
                repo_metadata=metadata,
                tree_summary=artifact.tree_summary,
                selected_files=filtered_context.selected_paths,
                filtered_out_files=filtered_context.filtered_out_paths,
                documentation_files=documentation_files,
                output_file=output_path.as_posix(),
                repo_chunk_index_file=repo_chunk_index_path.as_posix(),
                tree_analysis_plan=tree_analysis_plan.model_dump(mode="json"),
                tree_analysis_output_file=tree_analysis_output_path.as_posix(),
                repository_analysis=repository_analysis.model_dump(mode="json"),
                repository_analysis_output_file=repository_analysis_output_path.as_posix(),
                markdown_report_file=markdown_report_path.as_posix(),
            )

    @staticmethod
    def _get_documentation_paths(selected_files: list[str]) -> list[str]:
        documentation_paths: list[str] = []
        for path in selected_files:
            pure_path = PurePosixPath(path)
            lower_name = pure_path.name.lower()
            lower_path = pure_path.as_posix().lower()
            if lower_name.startswith("readme") or lower_path.startswith("docs/") or pure_path.suffix.lower() in DOCUMENTATION_EXTENSIONS:
                documentation_paths.append(path)
        return documentation_paths

    @staticmethod
    def _mark(
        reporter: RunProgressReporter | None,
        phase_id: str,
        subtask_id: str,
        status: str,
        detail: str,
    ) -> None:
        if reporter is None:
            return
        if status == "in-progress":
            reporter.start_subtask(phase_id, subtask_id, detail)
        elif status == "completed":
            reporter.complete_subtask(phase_id, subtask_id, detail)
        elif status == "skipped":
            reporter.skip_subtask(phase_id, subtask_id, detail)
        elif status == "failed":
            reporter.fail_subtask(phase_id, subtask_id, detail)

    @classmethod
    def _phase_progress_callback(cls, reporter: RunProgressReporter | None, phase_id: str):
        def callback(subtask_id: str, status: str, detail: str) -> None:
            cls._mark(reporter, phase_id, subtask_id, status, detail)

        return callback
