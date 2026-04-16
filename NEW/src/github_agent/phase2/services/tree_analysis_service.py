import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable

from pydantic import ValidationError

from src.config.settings import Settings, get_settings
from src.api_ui.services.run_store import RunProgressReporter
from src.github_agent.phase2.crew.tree_analysis_crew import run_tree_analysis_sequence
from src.github_agent.phase2.models.schemas import (
    ComponentName,
    EntrypointCandidates,
    Phase1RepoContextInput,
    SpecialistFocus,
    SpecialistName,
    Task1GroupingOutput,
    Task2ResolutionOutput,
    TreeAnalysisInput,
    TreeAnalysisOutputFile,
    TreeAnalysisPlan,
)
from src.github_agent.phase2.services.loader import Phase2Loader
from src.github_agent.phase2.services.preview_selector import PreviewSelector


class TreeAnalysisParserError(ValueError):
    """Raised when Tree Analysis Agent output cannot be parsed or validated."""


COMPONENT_ORDER: tuple[ComponentName, ...] = (
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
)

PRIORITY_COMPONENTS: tuple[ComponentName, ...] = (
    "overview_docs",
    "build_dependencies",
    "config_env",
    "backend",
    "frontend",
    "database_schema",
    "integrations",
    "infra_deployment",
)

SPECIALIST_GROUPS: dict[SpecialistName, tuple[ComponentName, ...]] = {
    "frontend_agent": ("frontend",),
    "backend_agent": ("backend", "database_schema", "workers"),
    "integration_security_agent": ("integrations", "config_env", "infra_deployment"),
    "platform_quality_agent": ("tests", "tools_scripts", "build_dependencies", "data_assets_dataset"),
}


class TreeAnalysisService:
    """Service layer for Phase 2 repository tree analysis."""

    def __init__(
        self,
        output_dir: Path,
        tree_analysis_model: str,
        loader: Phase2Loader | None = None,
        preview_selector: PreviewSelector | None = None,
        phase2_runner: Callable[..., tuple[object, object]] | None = None,
        preview_fetcher: Callable[[str, str, str, str], str] | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.tree_analysis_model = tree_analysis_model
        self.loader = loader or Phase2Loader()
        self.preview_selector = preview_selector or PreviewSelector()
        self.phase2_runner = phase2_runner
        self.preview_fetcher = preview_fetcher

    async def run_phase2_from_file(self, repo_context_path: str) -> TreeAnalysisPlan:
        plan, _ = await self.run_phase2_from_file_with_output(repo_context_path)
        return plan

    async def run_phase2_from_file_with_output(
        self,
        repo_context_path: str,
        progress_callback: Callable[[str, str, str], None] | None = None,
        run_reporter: RunProgressReporter | None = None,
    ) -> tuple[TreeAnalysisPlan, Path]:
        phase1_input = self.loader.load_phase1_artifact(repo_context_path)
        analysis_input = self.preview_selector.build_analysis_input(phase1_input)

        raw_task1_output, raw_task2_output = self._run_phase2(
            analysis_input,
            progress_callback=progress_callback,
            run_reporter=run_reporter,
        )
        task1_output = self.parse_task1_output(raw_task1_output)
        task2_output = self.parse_task2_output(raw_task2_output)

        if progress_callback is not None:
            progress_callback("build_tree_plan", "in-progress", "Building tree analysis plan")
        plan = self.build_final_plan(analysis_input, task1_output, task2_output)
        if progress_callback is not None:
            progress_callback("build_tree_plan", "completed", "Built tree analysis plan")
            progress_callback("derive_specialist_focus", "in-progress", "Deriving specialist focus")
        output_path = self.save_output(
            repo_context_path=repo_context_path,
            phase1_input=phase1_input,
            analysis_input=analysis_input,
            task1_output=task1_output,
            task2_output=task2_output,
            plan=plan,
        )
        if progress_callback is not None:
            progress_callback("derive_specialist_focus", "completed", "Derived specialist focus")
        return plan, output_path

    def build_final_plan(
        self,
        analysis_input: TreeAnalysisInput,
        task1_output: Task1GroupingOutput,
        task2_output: Task2ResolutionOutput,
    ) -> TreeAnalysisPlan:
        merged_groups = self._merge_groups(task1_output.groups, task2_output.resolved_groups)
        important_paths = self._build_important_paths(merged_groups)
        entrypoint_candidates = self._build_entrypoint_candidates(merged_groups)
        fetch_priority = self._build_fetch_priority(merged_groups, analysis_input.selected_files)
        unknowns = sorted(dict.fromkeys(task1_output.unknowns + task2_output.unknowns))

        return TreeAnalysisPlan(
            repo_type=task1_output.repo_type,
            confidence=self._calculate_confidence(task1_output, task2_output),
            important_paths=important_paths,
            entrypoint_candidates=entrypoint_candidates,
            groups=merged_groups,
            specialist_focus=self._build_specialist_focus(merged_groups),
            fetch_priority=fetch_priority,
            remaining_uncertain_files=task2_output.remaining_uncertain_files,
            unclassified_files=self._sorted_unique(task2_output.remaining_unclassified_files),
            unknowns=unknowns,
        )

    def save_output(
        self,
        repo_context_path: str,
        phase1_input: Phase1RepoContextInput,
        analysis_input: TreeAnalysisInput,
        task1_output: Task1GroupingOutput,
        task2_output: Task2ResolutionOutput,
        plan: TreeAnalysisPlan,
    ) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"{phase1_input.owner}__{phase1_input.repo}__tree_analysis_plan.json"
        payload = TreeAnalysisOutputFile(
            repo_url=phase1_input.repo_url,
            owner=phase1_input.owner,
            repo=phase1_input.repo,
            branch=phase1_input.branch,
            source_repo_context_file=Path(repo_context_path).as_posix(),
            analysis_input=analysis_input,
            task1_output=task1_output,
            task2_output=task2_output,
            plan=plan,
            created_at=datetime.now(timezone.utc),
        )
        output_path.write_text(json.dumps(payload.model_dump(mode="json"), indent=2), encoding="utf-8")
        return output_path

    def parse_task1_output(self, raw_output: object) -> Task1GroupingOutput:
        payload = self._coerce_to_payload(raw_output)
        try:
            return Task1GroupingOutput.model_validate(payload)
        except ValidationError as exc:
            raise TreeAnalysisParserError("Task 1 output failed schema validation.") from exc

    def parse_task2_output(self, raw_output: object) -> Task2ResolutionOutput:
        payload = self._coerce_to_payload(raw_output)
        try:
            return Task2ResolutionOutput.model_validate(payload)
        except ValidationError as exc:
            raise TreeAnalysisParserError("Task 2 output failed schema validation.") from exc

    def _run_phase2(
        self,
        analysis_input: TreeAnalysisInput,
        progress_callback: Callable[[str, str, str], None] | None = None,
        run_reporter: RunProgressReporter | None = None,
    ) -> tuple[object, object]:
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

        if self.phase2_runner is not None:
            return self.phase2_runner(analysis_input, model=self.tree_analysis_model)

        return run_tree_analysis_sequence(
            analysis_input,
            model=self.tree_analysis_model,
            preview_fetcher=preview_fetcher,
            progress_callback=progress_callback,
            run_reporter=run_reporter,
        )

    def _merge_groups(
        self,
        primary_groups: dict[ComponentName, list[str]],
        resolved_groups: dict[ComponentName, list[str]],
    ) -> dict[ComponentName, list[str]]:
        merged: dict[ComponentName, list[str]] = {}
        for component in COMPONENT_ORDER:
            combined = list(primary_groups.get(component, [])) + list(resolved_groups.get(component, []))
            normalized = self._sorted_unique(combined)
            if normalized:
                merged[component] = normalized
        return merged

    def _coerce_to_payload(self, raw_output: object) -> dict:
        if hasattr(raw_output, "pydantic") and raw_output.pydantic is not None:
            return raw_output.pydantic.model_dump()
        if hasattr(raw_output, "json_dict") and raw_output.json_dict is not None:
            return raw_output.json_dict
        if hasattr(raw_output, "raw"):
            raw_output = raw_output.raw
        if isinstance(raw_output, str):
            try:
                return json.loads(raw_output)
            except json.JSONDecodeError as exc:
                raise TreeAnalysisParserError("Tree analysis output was not valid JSON.") from exc
        if isinstance(raw_output, dict):
            return raw_output
        if hasattr(raw_output, "model_dump"):
            return raw_output.model_dump()
        raise TreeAnalysisParserError("Tree analysis output had an unsupported format.")

    @staticmethod
    def _sorted_unique(paths: list[str]) -> list[str]:
        return sorted(
            dict.fromkeys(path for path in paths if path),
            key=lambda item: (item.count("/"), item.lower()),
        )

    def _build_important_paths(self, groups: dict[ComponentName, list[str]]) -> list[str]:
        important: list[str] = []
        for component in PRIORITY_COMPONENTS:
            important.extend(groups.get(component, [])[:2])
        return self._sorted_unique(important)[:12]

    def _build_entrypoint_candidates(self, groups: dict[ComponentName, list[str]]) -> EntrypointCandidates:
        backend_candidates = self._detect_entrypoints(
            groups.get("backend", []) + groups.get("workers", []),
            allowed_suffixes={".py", ".js", ".ts", ".go", ".rb"},
        )
        frontend_candidates = self._detect_entrypoints(
            groups.get("frontend", []),
            allowed_suffixes={".jsx", ".tsx", ".js", ".ts", ".html", ".vue", ".svelte"},
        )
        return EntrypointCandidates(backend=backend_candidates, frontend=frontend_candidates)

    def _detect_entrypoints(self, paths: list[str], allowed_suffixes: set[str]) -> list[str]:
        scored_entrypoints: list[tuple[int, str]] = []
        for path in paths:
            pure_path = PurePosixPath(path)
            lower_name = pure_path.name.lower()
            suffix = pure_path.suffix.lower()
            if suffix not in allowed_suffixes:
                continue

            score = 0
            if lower_name in {"manage.py", "wsgi.py", "asgi.py"}:
                score += 100
            if lower_name.startswith(("main.", "app.", "server.", "index.")):
                score += 80
            if lower_name.startswith(("api_", "webhook_", "worker_")):
                score += 70
            if "api" in pure_path.stem.lower():
                score += 55
            if "server" in pure_path.stem.lower():
                score += 45
            if "app" == pure_path.stem.lower() or pure_path.stem.lower().endswith("_app"):
                score += 40
            score += max(0, 12 - pure_path.as_posix().count("/"))

            if score > 0:
                scored_entrypoints.append((score, path))

        scored_entrypoints.sort(key=lambda item: (-item[0], item[1].count("/"), item[1].lower()))
        return self._sorted_unique([path for _, path in scored_entrypoints])

    def _build_fetch_priority(self, groups: dict[ComponentName, list[str]], selected_files: list[str]) -> list[str]:
        fetch_priority: list[str] = []
        for component in PRIORITY_COMPONENTS:
            fetch_priority.extend(groups.get(component, [])[:2])
        if not fetch_priority:
            fetch_priority = selected_files[:10]
        return self._sorted_unique(fetch_priority)[:15]

    def _build_specialist_focus(self, groups: dict[ComponentName, list[str]]) -> list[SpecialistFocus]:
        focus_items: list[SpecialistFocus] = []
        for agent, owned_groups in SPECIALIST_GROUPS.items():
            assigned_paths: list[str] = []
            present_groups: list[ComponentName] = []
            for group in owned_groups:
                group_paths = groups.get(group, [])
                if group_paths:
                    present_groups.append(group)
                    assigned_paths.extend(group_paths)

            if not assigned_paths:
                continue

            focus_items.append(
                SpecialistFocus(
                    agent=agent,
                    groups=present_groups,
                    assigned_paths=self._sorted_unique(assigned_paths),
                    reason=(
                        "Derived from grouped components: "
                        + ", ".join(group.replace("_", "/") for group in present_groups)
                    ),
                )
            )

        return focus_items

    @staticmethod
    def _calculate_confidence(task1_output: Task1GroupingOutput, task2_output: Task2ResolutionOutput) -> float:
        total_review_targets = len(task1_output.uncertain_files) + len(task1_output.unclassified_files)
        remaining_review_targets = (
            len(task2_output.remaining_uncertain_files) + len(task2_output.remaining_unclassified_files)
        )
        if total_review_targets == 0:
            return 0.95
        resolved_ratio = (total_review_targets - remaining_review_targets) / total_review_targets
        return round(0.6 + (resolved_ratio * 0.3), 2)

def create_tree_analysis_service(
    settings: Settings | None = None,
    preview_fetcher: Callable[[str, str, str, str], str] | None = None,
) -> TreeAnalysisService:
    active_settings = settings or get_settings()
    return TreeAnalysisService(
        output_dir=active_settings.output_dir,
        tree_analysis_model=active_settings.tree_analysis_model,
        preview_fetcher=preview_fetcher,
    )
