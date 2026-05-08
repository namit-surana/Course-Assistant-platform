from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from src.api_ui.models.schemas import (
    AnalysisRunState,
    ItemStatus,
    RunEventKind,
    RunEventState,
    RunKind,
    RunPhaseState,
    build_default_run_phases,
)
from src.api_ui.services.audit_log_service import AuditLogService
from src.github_agent.phase1.models.schemas import AnalyzeResponse


class RunNotFoundError(KeyError):
    """Raised when a requested run id does not exist."""


class AnalysisRunStore:
    """In-memory store for live analysis runs."""

    def __init__(self, audit_log_service: AuditLogService | None = None) -> None:
        self._lock = Lock()
        self._runs: dict[str, AnalysisRunState] = {}
        self._event_ids: dict[str, int] = {}
        self._audit_log_service = audit_log_service

    def create_run(
        self,
        request,
        *,
        phases: list[RunPhaseState] | None = None,
        kind: RunKind = "repo",
        label: str | None = None,
    ) -> AnalysisRunState:
        resolved_phases = phases if phases is not None else build_default_run_phases()
        run = AnalysisRunState(
            request=request,
            phases=resolved_phases,
            kind=kind,
            label=label,
        )
        with self._lock:
            self._runs[run.id] = run
            self._event_ids[run.id] = 0
            self._log(
                run.id,
                "run-created",
                {
                    "kind": kind,
                    "status": run.status,
                    "request": request.model_dump(mode="json") if request is not None else None,
                },
            )
            return run.model_copy(deep=True)

    def get_run(self, run_id: str) -> AnalysisRunState:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise RunNotFoundError(run_id)
            return run.model_copy(deep=True)

    def list_runs(self, limit: int = 20) -> list[AnalysisRunState]:
        with self._lock:
            runs = sorted(
                self._runs.values(),
                key=lambda run: run.updated_at,
                reverse=True,
            )
            return [run.model_copy(deep=True) for run in runs[:limit]]

    def start_run(self, run_id: str) -> None:
        with self._lock:
            run = self._require_run(run_id)
            run.status = "running"
            self._touch(run)
            self._log(run_id, "run-started", {"status": run.status})

    def set_repo_details(self, run_id: str, owner: str, repo: str, branch: str) -> None:
        with self._lock:
            run = self._require_run(run_id)
            run.owner = owner
            run.repo = repo
            run.branch = branch
            self._touch(run)
            self._log(
                run_id,
                "repo-details",
                {
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                },
            )

    def set_current_activity(self, run_id: str, message: str | None) -> None:
        with self._lock:
            run = self._require_run(run_id)
            run.current_activity = message
            self._touch(run)

    def patch_subtask(
        self,
        run_id: str,
        phase_id: str,
        subtask_id: str,
        *,
        detail: str | None = None,
        badges: list[str] | None = None,
    ) -> None:
        with self._lock:
            run = self._require_run(run_id)
            phase = self._require_phase(run, phase_id)
            subtask = self._require_subtask(phase, subtask_id)
            if detail is not None:
                subtask.detail = detail
            if badges is not None:
                subtask.badges = badges
            self._touch(run)

    def append_event(
        self,
        run_id: str,
        *,
        kind: RunEventKind,
        message: str,
        phase_id: str | None = None,
        subtask_id: str | None = None,
        badges: list[str] | None = None,
    ) -> None:
        with self._lock:
            run = self._require_run(run_id)
            if phase_id is not None and subtask_id is not None:
                phase = self._require_phase(run, phase_id)
                subtask = self._require_subtask(phase, subtask_id)
                subtask.activity_log.append(message)
                if len(subtask.activity_log) > 3:
                    subtask.activity_log = subtask.activity_log[-3:]
            next_event_id = self._event_ids.get(run_id, 0) + 1
            self._event_ids[run_id] = next_event_id
            run.events.append(
                RunEventState(
                    id=next_event_id,
                    phase_id=phase_id,
                    subtask_id=subtask_id,
                    kind=kind,
                    message=message,
                    badges=badges or [],
                )
            )
            if len(run.events) > 80:
                run.events = run.events[-80:]
            run.current_activity = message
            self._touch(run)
            self._log(
                run_id,
                "run-event",
                {
                    "kind": kind,
                    "message": message,
                    "phase_id": phase_id,
                    "subtask_id": subtask_id,
                    "badges": badges or [],
                },
            )

    def update_subtask(
        self,
        run_id: str,
        phase_id: str,
        subtask_id: str,
        status: ItemStatus,
        *,
        detail: str | None = None,
        badges: list[str] | None = None,
    ) -> None:
        with self._lock:
            run = self._require_run(run_id)
            phase = self._require_phase(run, phase_id)
            subtask = self._require_subtask(phase, subtask_id)
            subtask.status = status
            if detail is not None:
                subtask.detail = detail
            if badges is not None:
                subtask.badges = badges
            phase.status = self._derive_phase_status(phase.subtasks)
            self._touch(run)
            self._log(
                run_id,
                "subtask-status",
                {
                    "phase_id": phase_id,
                    "phase_status": phase.status,
                    "subtask_id": subtask_id,
                    "subtask_status": status,
                    "detail": detail,
                    "badges": badges or [],
                },
            )

    def complete_run_simple(self, run_id: str, result: dict) -> None:
        """Mark a non-github (PPT/video) run as completed with a generic dict result."""
        with self._lock:
            run = self._require_run(run_id)
            run.status = "completed"
            run.result_simple = result
            run.current_activity = "Analysis completed"
            run.completed_at = datetime.now(timezone.utc)
            run.updated_at = run.completed_at
            run.revision += 1
            self._log(
                run_id,
                "run-completed",
                {"status": run.status, "kind": run.kind},
            )

    def complete_run(self, run_id: str, result: AnalyzeResponse, markdown_report_content: str | None) -> None:
        with self._lock:
            run = self._require_run(run_id)
            run.status = "completed"
            run.result = result
            run.markdown_report_content = markdown_report_content
            run.current_activity = "Analysis completed"
            run.completed_at = datetime.now(timezone.utc)
            run.updated_at = run.completed_at
            run.revision += 1
            self._log(
                run_id,
                "run-completed",
                {
                    "status": run.status,
                    "result": result.model_dump(mode="json"),
                    "has_markdown_report_content": markdown_report_content is not None,
                },
            )

    def fail_run(self, run_id: str, error_message: str) -> None:
        with self._lock:
            run = self._require_run(run_id)
            for phase in run.phases:
                for subtask in phase.subtasks:
                    if subtask.status == "in-progress":
                        subtask.status = "failed"
                        if not subtask.detail:
                            subtask.detail = error_message
                phase.status = self._derive_phase_status(phase.subtasks)
            run.status = "failed"
            run.error = error_message
            run.current_activity = error_message
            run.completed_at = datetime.now(timezone.utc)
            run.updated_at = run.completed_at
            run.revision += 1
            self._log(
                run_id,
                "run-failed",
                {
                    "status": run.status,
                    "error": error_message,
                },
            )

    @staticmethod
    def _derive_phase_status(subtasks) -> ItemStatus:
        statuses = [item.status for item in subtasks]
        if any(status == "failed" for status in statuses):
            return "failed"
        if any(status == "in-progress" for status in statuses):
            return "in-progress"
        if statuses and all(status in {"completed", "skipped"} for status in statuses):
            return "completed"
        if any(status == "completed" for status in statuses):
            return "in-progress"
        return "pending"

    def _require_run(self, run_id: str) -> AnalysisRunState:
        run = self._runs.get(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    @staticmethod
    def _touch(run: AnalysisRunState) -> None:
        run.updated_at = datetime.now(timezone.utc)
        run.revision += 1

    @staticmethod
    def _require_phase(run: AnalysisRunState, phase_id: str):
        for phase in run.phases:
            if phase.id == phase_id:
                return phase
        raise RunNotFoundError(f"Unknown phase: {phase_id}")

    @staticmethod
    def _require_subtask(phase, subtask_id: str):
        for subtask in phase.subtasks:
            if subtask.id == subtask_id:
                return subtask
        raise RunNotFoundError(f"Unknown subtask: {subtask_id}")

    def _log(self, run_id: str, event_type: str, payload: dict) -> None:
        if self._audit_log_service is None:
            return
        self._audit_log_service.log(run_id, event_type, payload)


class RunProgressReporter:
    """Convenience wrapper for updating a single run from the analysis pipeline."""

    def __init__(self, store: AnalysisRunStore, run_id: str) -> None:
        self.store = store
        self.run_id = run_id

    def start(self) -> None:
        self.store.start_run(self.run_id)

    def repo_details(self, owner: str, repo: str, branch: str) -> None:
        self.store.set_repo_details(self.run_id, owner, repo, branch)

    def activity(self, message: str) -> None:
        self.store.set_current_activity(self.run_id, message)

    def patch_subtask(self, phase_id: str, subtask_id: str, detail: str | None = None, badges: list[str] | None = None) -> None:
        self.store.patch_subtask(self.run_id, phase_id, subtask_id, detail=detail, badges=badges)

    def event(
        self,
        kind: RunEventKind,
        message: str,
        *,
        phase_id: str | None = None,
        subtask_id: str | None = None,
        badges: list[str] | None = None,
    ) -> None:
        self.store.append_event(
            self.run_id,
            kind=kind,
            message=message,
            phase_id=phase_id,
            subtask_id=subtask_id,
            badges=badges,
        )

    def start_subtask(self, phase_id: str, subtask_id: str, detail: str | None = None, badges: list[str] | None = None) -> None:
        self.store.update_subtask(self.run_id, phase_id, subtask_id, "in-progress", detail=detail, badges=badges)
        if detail is not None:
            self.activity(detail)
            self.event("task-started", detail, phase_id=phase_id, subtask_id=subtask_id, badges=badges)

    def complete_subtask(self, phase_id: str, subtask_id: str, detail: str | None = None, badges: list[str] | None = None) -> None:
        self.store.update_subtask(self.run_id, phase_id, subtask_id, "completed", detail=detail, badges=badges)
        if detail is not None:
            self.activity(detail)
            self.event("task-completed", detail, phase_id=phase_id, subtask_id=subtask_id, badges=badges)

    def skip_subtask(self, phase_id: str, subtask_id: str, detail: str) -> None:
        self.store.update_subtask(self.run_id, phase_id, subtask_id, "skipped", detail=detail)
        self.event("info", detail, phase_id=phase_id, subtask_id=subtask_id)

    def fail_subtask(self, phase_id: str, subtask_id: str, detail: str) -> None:
        self.store.update_subtask(self.run_id, phase_id, subtask_id, "failed", detail=detail)
        self.activity(detail)
        self.event("error", detail, phase_id=phase_id, subtask_id=subtask_id)

    def complete_run(self, result: AnalyzeResponse, markdown_report_content: str | None) -> None:
        self.store.complete_run(self.run_id, result, markdown_report_content)

    def complete_run_simple(self, result: dict) -> None:
        self.store.complete_run_simple(self.run_id, result)

    def fail_run(self, error_message: str) -> None:
        self.store.fail_run(self.run_id, error_message)
