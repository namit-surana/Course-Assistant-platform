from __future__ import annotations

import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from src.config.settings import Settings, get_settings
from src.api_ui.services.run_store import RunProgressReporter
from src.github_agent.phase2.models.schemas import Phase1RepoContextInput, TreeAnalysisOutputFile
from src.github_agent.phase3.crew.repository_analysis_crew import (
    run_backend_review,
    run_final_report,
    run_frontend_review,
    run_integration_security_review,
    run_platform_quality_review,
    run_repo_intake_analysis,
)
from src.github_agent.phase3.models.schemas import (
    FinalRepositoryAnalysis,
    RepoIntakeOutput,
    RepositoryAnalysisInput,
    RepositoryAnalysisOutputFile,
    RepositoryAnalysisRunResult,
    SpecialistPromptInput,
    SpecialistAnalysisOutput,
    SpecialistSynthesisSummary,
)

logger = logging.getLogger(__name__)


class RepositoryAnalysisParserError(ValueError):
    """Raised when final repository analysis cannot be parsed or validated."""


class RepositoryAnalysisService:
    """Service layer for the production-grade repository analysis pass."""

    def __init__(
        self,
        output_dir: Path,
        repository_analysis_model: str,
        analysis_runner: Callable[..., object] | None = None,
        preview_fetcher: Callable[[str, str, str, str], str] | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.repository_analysis_model = repository_analysis_model
        self.analysis_runner = analysis_runner
        self.preview_fetcher = preview_fetcher

    async def run_phase3_from_files(self, repo_context_path: str, tree_analysis_path: str) -> FinalRepositoryAnalysis:
        analysis, _, _ = await self.run_phase3_from_files_with_output(repo_context_path, tree_analysis_path)
        return analysis

    async def run_phase3_from_files_with_output(
        self,
        repo_context_path: str,
        tree_analysis_path: str,
        progress_callback: Callable[[str, str, str], None] | None = None,
        run_reporter: RunProgressReporter | None = None,
    ) -> tuple[FinalRepositoryAnalysis, Path, Path]:
        phase1_input = self._load_phase1_artifact(repo_context_path)
        tree_analysis_output = self._load_tree_analysis_artifact(tree_analysis_path)
        self._validate_source_artifacts(phase1_input, tree_analysis_output)

        analysis_input = RepositoryAnalysisInput(
            repo_url=phase1_input.repo_url,
            owner=phase1_input.owner,
            repo=phase1_input.repo,
            branch=phase1_input.branch,
            repo_metadata=phase1_input.repo_metadata,
            tree_summary=phase1_input.tree_summary,
            selected_files=phase1_input.selected_files,
            documentation_previews=phase1_input.documentation_files,
            tree_analysis_plan=tree_analysis_output.plan,
        )
        run_result = self._coerce_run_result(await self._run_phase3(analysis_input, progress_callback, run_reporter))
        markdown = self.render_markdown_report(analysis_input, run_result.final_analysis)
        output_path, markdown_path = self.save_output(
            repo_context_path=repo_context_path,
            tree_analysis_path=tree_analysis_path,
            analysis_input=analysis_input,
            run_result=run_result,
            markdown=markdown,
        )
        return run_result.final_analysis, output_path, markdown_path

    async def _run_phase3(
        self,
        analysis_input: RepositoryAnalysisInput,
        progress_callback: Callable[[str, str, str], None] | None = None,
        run_reporter: RunProgressReporter | None = None,
    ) -> object:
        preview_fetcher: Callable[[str, int, int], str] | None = None
        if self.preview_fetcher is not None:
            preview_fetcher = lambda path, start_line=1, max_lines=80: self.preview_fetcher(
                analysis_input.owner,
                analysis_input.repo,
                analysis_input.branch,
                path,
                start_line=start_line,
                max_lines=max_lines,
            )

        if self.analysis_runner is not None:
            return self.analysis_runner(
                analysis_input,
                model=self.repository_analysis_model,
                preview_fetcher=preview_fetcher,
            )

        result = await self._run_default_sequence(analysis_input, preview_fetcher, progress_callback, run_reporter)
        logger.info("Phase 3 repository analysis sequence completed")
        return result

    async def _run_default_sequence(
        self,
        analysis_input: RepositoryAnalysisInput,
        preview_fetcher: Callable[[str], str] | None,
        progress_callback: Callable[[str, str, str], None] | None,
        run_reporter: RunProgressReporter | None,
    ) -> RepositoryAnalysisRunResult:
        logger.info("Phase 3 repo intake started")
        self._report_progress(progress_callback, "repo_intake", "in-progress", "Phase 3 repo intake started")
        intake_output = await asyncio.to_thread(
            run_repo_intake_analysis,
            analysis_input,
            self.repository_analysis_model,
            run_reporter,
        )
        logger.info("Phase 3 repo intake completed")
        self._report_progress(progress_callback, "repo_intake", "completed", "Phase 3 repo intake completed")

        specialist_outputs = await self._run_specialists_in_parallel(
            analysis_input=analysis_input,
            intake_output=intake_output,
            preview_fetcher=preview_fetcher,
            progress_callback=progress_callback,
            run_reporter=run_reporter,
        )

        logger.info("Phase 3 final report started")
        self._report_progress(progress_callback, "final_report", "in-progress", "Phase 3 final report started")
        specialist_summaries = self._build_specialist_summaries(
            specialist_outputs["frontend_output"],
            specialist_outputs["backend_output"],
            specialist_outputs["integration_security_output"],
            specialist_outputs["platform_quality_output"],
        )
        final_analysis = await asyncio.to_thread(
            run_final_report,
            analysis_input,
            intake_output,
            specialist_summaries["frontend_summary"],
            specialist_summaries["backend_summary"],
            specialist_summaries["integration_security_summary"],
            specialist_summaries["platform_quality_summary"],
            self.repository_analysis_model,
            run_reporter,
        )
        logger.info("Phase 3 final report completed")
        self._report_progress(progress_callback, "final_report", "completed", "Phase 3 final report completed")

        return RepositoryAnalysisRunResult(
            intake_output=intake_output,
            frontend_output=specialist_outputs["frontend_output"],
            backend_output=specialist_outputs["backend_output"],
            integration_security_output=specialist_outputs["integration_security_output"],
            platform_quality_output=specialist_outputs["platform_quality_output"],
            final_analysis=final_analysis,
        )

    async def _run_specialists_in_parallel(
        self,
        *,
        analysis_input: RepositoryAnalysisInput,
        intake_output: RepoIntakeOutput,
        preview_fetcher: Callable[[str], str] | None,
        progress_callback: Callable[[str, str, str], None] | None,
        run_reporter: RunProgressReporter | None,
    ) -> dict[str, SpecialistAnalysisOutput]:
        frontend_input = self._build_specialist_prompt_input(analysis_input, intake_output, "frontend_agent")
        backend_input = self._build_specialist_prompt_input(analysis_input, intake_output, "backend_agent")
        integration_security_input = self._build_specialist_prompt_input(
            analysis_input,
            intake_output,
            "integration_security_agent",
        )
        platform_quality_input = self._build_specialist_prompt_input(
            analysis_input,
            intake_output,
            "platform_quality_agent",
        )

        tasks = {
            "frontend_output": asyncio.create_task(
                asyncio.to_thread(
                    self._run_specialist_or_skip,
                    step_name="frontend review",
                    subtask_id="frontend_review",
                    specialist_input=frontend_input,
                    runner=lambda: run_frontend_review(
                        analysis_input,
                        frontend_input,
                        model=self.repository_analysis_model,
                        preview_fetcher=preview_fetcher,
                        run_reporter=run_reporter,
                    ),
                    progress_callback=progress_callback,
                )
            ),
            "backend_output": asyncio.create_task(
                asyncio.to_thread(
                    self._run_specialist_or_skip,
                    step_name="backend review",
                    subtask_id="backend_review",
                    specialist_input=backend_input,
                    runner=lambda: run_backend_review(
                        analysis_input,
                        backend_input,
                        model=self.repository_analysis_model,
                        preview_fetcher=preview_fetcher,
                        run_reporter=run_reporter,
                    ),
                    progress_callback=progress_callback,
                )
            ),
            "integration_security_output": asyncio.create_task(
                asyncio.to_thread(
                    self._run_specialist_or_skip,
                    step_name="integration and security review",
                    subtask_id="integration_security_review",
                    specialist_input=integration_security_input,
                    runner=lambda: run_integration_security_review(
                        analysis_input,
                        integration_security_input,
                        model=self.repository_analysis_model,
                        preview_fetcher=preview_fetcher,
                        run_reporter=run_reporter,
                    ),
                    progress_callback=progress_callback,
                )
            ),
            "platform_quality_output": asyncio.create_task(
                asyncio.to_thread(
                    self._run_specialist_or_skip,
                    step_name="platform quality review",
                    subtask_id="platform_quality_review",
                    specialist_input=platform_quality_input,
                    runner=lambda: run_platform_quality_review(
                        analysis_input,
                        platform_quality_input,
                        model=self.repository_analysis_model,
                        preview_fetcher=preview_fetcher,
                        run_reporter=run_reporter,
                    ),
                    progress_callback=progress_callback,
                )
            ),
        }
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results, strict=True))

    def _run_specialist_or_skip(
        self,
        *,
        step_name: str,
        subtask_id: str,
        specialist_input: SpecialistPromptInput,
        runner: Callable[[], SpecialistAnalysisOutput],
        progress_callback: Callable[[str, str, str], None] | None,
    ) -> SpecialistAnalysisOutput:
        if not specialist_input.assigned_paths:
            logger.info("Phase 3 %s skipped", step_name)
            self._report_progress(
                progress_callback,
                subtask_id,
                "skipped",
                "Skipped because tree analysis assigned no relevant files to this specialist.",
            )
            return SpecialistAnalysisOutput(
                applicable=False,
                summary="Skipped because tree analysis assigned no relevant files to this specialist.",
            )

        logger.info("Phase 3 %s started", step_name)
        self._report_progress(progress_callback, subtask_id, "in-progress", f"Phase 3 {step_name} started")
        result = self._normalize_specialist_output(runner())
        logger.info(
            "Phase 3 %s output size: summary_chars=%s runtime_items=%s architecture_items=%s risk_items=%s "
            "strength_items=%s question_items=%s evidence_paths=%s serialized_chars=%s",
            step_name,
            len(result.summary),
            len(result.runtime_behavior),
            len(result.architecture_patterns),
            len(result.risks),
            len(result.strengths),
            len(result.intelligent_questions),
            len(result.evidence_paths),
            len(result.model_dump_json()),
        )
        logger.info("Phase 3 %s completed", step_name)
        self._report_progress(progress_callback, subtask_id, "completed", f"Phase 3 {step_name} completed")
        return result

    @staticmethod
    def _build_specialist_summaries(
        frontend_output: SpecialistAnalysisOutput,
        backend_output: SpecialistAnalysisOutput,
        integration_security_output: SpecialistAnalysisOutput,
        platform_quality_output: SpecialistAnalysisOutput,
    ) -> dict[str, SpecialistSynthesisSummary]:
        return {
            "frontend_summary": RepositoryAnalysisService._build_specialist_summary(frontend_output),
            "backend_summary": RepositoryAnalysisService._build_specialist_summary(backend_output),
            "integration_security_summary": RepositoryAnalysisService._build_specialist_summary(
                integration_security_output
            ),
            "platform_quality_summary": RepositoryAnalysisService._build_specialist_summary(platform_quality_output),
        }

    @staticmethod
    def _build_specialist_summary(output: SpecialistAnalysisOutput) -> SpecialistSynthesisSummary:
        return SpecialistSynthesisSummary(
            applicable=output.applicable,
            summary=output.summary,
            top_runtime_behavior=list(output.runtime_behavior[:3]),
            top_architecture_patterns=list(output.architecture_patterns[:3]),
            top_risks=list(output.risks[:4]),
            top_strengths=list(output.strengths[:3]),
            top_questions=list(output.intelligent_questions[:3]),
            evidence_paths=list(output.evidence_paths[:8]),
        )

    @staticmethod
    def _normalize_specialist_output(output: SpecialistAnalysisOutput) -> SpecialistAnalysisOutput:
        if not output.applicable:
            return SpecialistAnalysisOutput(
                applicable=False,
                summary=RepositoryAnalysisService._truncate_text(output.summary, 220),
            )

        return SpecialistAnalysisOutput(
            applicable=True,
            summary=RepositoryAnalysisService._truncate_text(output.summary, 700),
            runtime_behavior=RepositoryAnalysisService._trim_unique_list(output.runtime_behavior, 6, 240),
            architecture_patterns=RepositoryAnalysisService._trim_unique_list(output.architecture_patterns, 5, 220),
            risks=RepositoryAnalysisService._trim_unique_list(output.risks, 6, 260),
            strengths=RepositoryAnalysisService._trim_unique_list(output.strengths, 5, 220),
            intelligent_questions=RepositoryAnalysisService._trim_unique_list(output.intelligent_questions, 5, 220),
            evidence_paths=RepositoryAnalysisService._trim_unique_list(output.evidence_paths, 10, 180),
        )

    @staticmethod
    def _trim_unique_list(items: list[str], limit: int, char_limit: int) -> list[str]:
        seen: set[str] = set()
        trimmed: list[str] = []
        for item in items:
            normalized = " ".join(item.split()).strip()
            if not normalized:
                continue
            dedupe_key = normalized.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            trimmed.append(RepositoryAnalysisService._truncate_text(normalized, char_limit))
            if len(trimmed) >= limit:
                break
        return trimmed

    @staticmethod
    def _truncate_text(value: str, limit: int) -> str:
        normalized = " ".join(value.split()).strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."

    def save_output(
        self,
        repo_context_path: str,
        tree_analysis_path: str,
        analysis_input: RepositoryAnalysisInput,
        run_result: RepositoryAnalysisRunResult,
        markdown: str,
    ) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self.output_dir / f"{analysis_input.owner}__{analysis_input.repo}__repository_analysis.json"
        markdown_path = self.output_dir / f"{analysis_input.owner}__{analysis_input.repo}__repository_report.md"
        markdown_path.write_text(markdown, encoding="utf-8")

        payload = RepositoryAnalysisOutputFile(
            repo_url=analysis_input.repo_url,
            owner=analysis_input.owner,
            repo=analysis_input.repo,
            branch=analysis_input.branch,
            source_repo_context_file=Path(repo_context_path).as_posix(),
            source_tree_analysis_file=Path(tree_analysis_path).as_posix(),
            analysis_input=analysis_input,
            intake_output=run_result.intake_output,
            frontend_output=run_result.frontend_output,
            backend_output=run_result.backend_output,
            integration_security_output=run_result.integration_security_output,
            platform_quality_output=run_result.platform_quality_output,
            final_analysis=run_result.final_analysis,
            markdown_report_file=markdown_path.as_posix(),
            created_at=datetime.now(timezone.utc),
        )
        output_path.write_text(json.dumps(payload.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path, markdown_path

    def render_markdown_report(
        self,
        analysis_input: RepositoryAnalysisInput,
        final_analysis: FinalRepositoryAnalysis,
    ) -> str:
        lines = [
            f"# {final_analysis.report_title}",
            "",
            f"- Repository: `{analysis_input.owner}/{analysis_input.repo}`",
            f"- Branch: `{analysis_input.branch}`",
            f"- Source: {analysis_input.repo_url}",
            "",
            "## Executive Summary",
            "",
            final_analysis.executive_summary.strip(),
            "",
            "## Repository Overview",
            "",
            final_analysis.repository_overview.strip(),
            "",
        ]
        lines.extend(self._render_list_section("Component Summary", final_analysis.component_summary))
        lines.extend(self._render_list_section("Runtime Behavior", final_analysis.runtime_behavior))
        lines.extend(self._render_list_section("Architecture Patterns", final_analysis.architecture_patterns))
        lines.extend(self._render_list_section("Risks & Weaknesses", final_analysis.risks_and_weaknesses))
        lines.extend(
            [
                "## Quality Assessment",
                "",
                final_analysis.quality_assessment.strip(),
                "",
            ]
        )
        lines.extend(self._render_list_section("Strengths", final_analysis.strengths))
        lines.extend(self._render_list_section("Intelligent Questions", final_analysis.intelligent_questions))
        lines.extend(self._render_list_section("Recommended Next Steps", final_analysis.recommended_next_steps))
        lines.extend(self._render_list_section("Evidence Paths", final_analysis.evidence_paths))
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _render_list_section(title: str, items: list[str]) -> list[str]:
        lines = [f"## {title}", ""]
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- None identified.")
        lines.append("")
        return lines

    @staticmethod
    def _load_phase1_artifact(repo_context_path: str) -> Phase1RepoContextInput:
        try:
            return Phase1RepoContextInput.model_validate_json(Path(repo_context_path).read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise RepositoryAnalysisParserError("Repo context artifact could not be loaded for final analysis.") from exc

    @staticmethod
    def _load_tree_analysis_artifact(tree_analysis_path: str) -> TreeAnalysisOutputFile:
        try:
            return TreeAnalysisOutputFile.model_validate_json(Path(tree_analysis_path).read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise RepositoryAnalysisParserError("Tree analysis artifact could not be loaded for final analysis.") from exc

    @staticmethod
    def _validate_source_artifacts(
        phase1_input: Phase1RepoContextInput,
        tree_analysis_output: TreeAnalysisOutputFile,
    ) -> None:
        left = (phase1_input.owner, phase1_input.repo, phase1_input.branch)
        right = (tree_analysis_output.owner, tree_analysis_output.repo, tree_analysis_output.branch)
        if left != right:
            raise RepositoryAnalysisParserError(
                "Repo context artifact and tree analysis artifact refer to different repositories or branches."
            )

    @staticmethod
    def _coerce_run_result(raw_result: object) -> RepositoryAnalysisRunResult:
        try:
            if isinstance(raw_result, RepositoryAnalysisRunResult):
                return raw_result
            if isinstance(raw_result, dict):
                return RepositoryAnalysisRunResult.model_validate(raw_result)
            if hasattr(raw_result, "model_dump"):
                return RepositoryAnalysisRunResult.model_validate(raw_result.model_dump())
        except ValidationError as exc:
            raise RepositoryAnalysisParserError("Repository analysis output failed schema validation.") from exc
        raise RepositoryAnalysisParserError("Repository analysis output had an unsupported format.")

    @staticmethod
    def _find_specialist_focus(analysis_input: RepositoryAnalysisInput, agent_name: str):
        for focus in analysis_input.tree_analysis_plan.specialist_focus:
            if focus.agent == agent_name:
                return focus
        return None

    @classmethod
    def _build_specialist_prompt_input(
        cls,
        analysis_input: RepositoryAnalysisInput,
        intake_output: RepoIntakeOutput,
        agent_name: str,
    ) -> SpecialistPromptInput:
        focus = cls._find_specialist_focus(analysis_input, agent_name)
        if focus is None:
            focus_groups = []
            assigned_paths = []
            focus_reason = "No specialist assignment was derived from the tree analysis plan."
        else:
            focus_groups = list(focus.groups)
            assigned_paths = list(focus.assigned_paths)
            focus_reason = focus.reason

        return SpecialistPromptInput(
            repo_url=analysis_input.repo_url,
            owner=analysis_input.owner,
            repo=analysis_input.repo,
            branch=analysis_input.branch,
            repo_type=analysis_input.tree_analysis_plan.repo_type,
            repo_summary=intake_output.repo_summary,
            stack_summary=list(intake_output.stack_summary),
            architecture_hypotheses=list(intake_output.architecture_hypotheses),
            important_paths=list(analysis_input.tree_analysis_plan.important_paths),
            entrypoint_candidates=analysis_input.tree_analysis_plan.entrypoint_candidates,
            focus_groups=focus_groups,
            assigned_paths=assigned_paths,
            focus_reason=focus_reason,
        )

    @staticmethod
    def _report_progress(
        callback: Callable[[str, str, str], None] | None,
        subtask_id: str,
        status: str,
        detail: str,
    ) -> None:
        if callback is not None:
            callback(subtask_id, status, detail)


def create_repository_analysis_service(
    settings: Settings | None = None,
    preview_fetcher: Callable[[str, str, str, str], str] | None = None,
) -> RepositoryAnalysisService:
    active_settings = settings or get_settings()
    return RepositoryAnalysisService(
        output_dir=active_settings.output_dir,
        repository_analysis_model=active_settings.repository_analysis_model,
        preview_fetcher=preview_fetcher,
    )
