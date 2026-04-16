import json
from pathlib import Path

from src.api_ui.services.audit_log_service import AuditLogService
from src.api_ui.services.run_store import AnalysisRunStore, RunProgressReporter
from src.github_agent.phase1.models.schemas import AnalyzeRequest, AnalyzeResponse, RepoMetadata, TreeSummary


def test_create_run_builds_default_phase_timeline() -> None:
    store = AnalysisRunStore()

    run = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/Hello-World", branch="main")
    )

    assert run.status == "queued"
    assert [phase.id for phase in run.phases] == ["phase1", "phase2", "phase3", "outputs"]
    assert run.phases[0].subtasks[0].id == "parse_repo"
    assert run.phases[2].subtasks[-1].id == "final_report"


def test_progress_reporter_updates_subtask_status_and_completion() -> None:
    store = AnalysisRunStore()
    run = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/Hello-World", branch="main")
    )
    reporter = RunProgressReporter(store, run.id)

    reporter.start()
    reporter.start_subtask("phase1", "parse_repo", "Parsing repository URL")
    reporter.complete_subtask("phase1", "parse_repo", "Repository URL parsed")
    reporter.complete_run(
        AnalyzeResponse(
            status="success",
            repo_url="https://github.com/octocat/Hello-World",
            owner="octocat",
            repo="Hello-World",
            branch="main",
            repo_metadata=RepoMetadata(
                full_name="octocat/Hello-World",
                default_branch="main",
            ),
            tree_summary=TreeSummary(
                total_items=1,
                total_blobs=1,
                total_trees=0,
                filtered_out_count=0,
                selected_file_count=1,
            ),
            selected_files=["README.md"],
            filtered_out_files=[],
            documentation_files=[],
            output_file="outputs/repo_context.json",
        ),
        "# Report\n",
    )

    updated = store.get_run(run.id)

    assert updated.status == "completed"
    assert updated.phases[0].subtasks[0].status == "completed"
    assert updated.markdown_report_content == "# Report\n"
    assert updated.events[0].kind == "task-started"
    assert updated.events[1].kind == "task-completed"
    assert updated.revision > 0


def test_progress_reporter_can_append_live_events_and_patch_subtasks() -> None:
    store = AnalysisRunStore()
    run = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/Hello-World", branch="main")
    )
    reporter = RunProgressReporter(store, run.id)

    reporter.start()
    reporter.start_subtask("phase3", "backend_review", "Phase 3 backend review started")
    reporter.patch_subtask("phase3", "backend_review", detail="Backend Reviewer is analyzing this step", badges=["Backend Reviewer"])
    reporter.event(
        "tool-started",
        "Using fetch_repo_file_preview on src/api.py",
        phase_id="phase3",
        subtask_id="backend_review",
        badges=["fetch_repo_file_preview"],
    )

    updated = store.get_run(run.id)
    backend_review = updated.phases[2].subtasks[2]

    assert backend_review.detail == "Backend Reviewer is analyzing this step"
    assert backend_review.badges == ["Backend Reviewer"]
    assert backend_review.activity_log[-1] == "Using fetch_repo_file_preview on src/api.py"
    assert updated.events[-1].kind == "tool-started"
    assert updated.events[-1].message == "Using fetch_repo_file_preview on src/api.py"


def test_fail_run_marks_active_subtask_and_phase_failed() -> None:
    store = AnalysisRunStore()
    run = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/Hello-World", branch="main")
    )
    reporter = RunProgressReporter(store, run.id)

    reporter.start()
    reporter.start_subtask("phase1", "fetch_tree", "Fetching repository tree")
    reporter.fail_run("Git Repository is empty.")

    updated = store.get_run(run.id)

    assert updated.status == "failed"
    assert updated.error == "Git Repository is empty."
    assert updated.phases[0].status == "failed"
    assert updated.phases[0].subtasks[2].status == "failed"
    assert updated.phases[0].subtasks[2].detail == "Fetching repository tree"


def test_audit_log_service_persists_run_events(workspace_tmp_path: Path) -> None:
    audit_service = AuditLogService(workspace_tmp_path / "run_audit")
    store = AnalysisRunStore(audit_log_service=audit_service)
    run = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/Hello-World", branch="main")
    )
    reporter = RunProgressReporter(store, run.id)

    reporter.start()
    reporter.start_subtask("phase1", "parse_repo", "Parsing repository URL")
    reporter.complete_subtask("phase1", "parse_repo", "Repository URL parsed")
    reporter.fail_run("Synthetic failure")

    audit_path = workspace_tmp_path / "run_audit" / f"{run.id}.jsonl"
    lines = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]

    assert audit_path.exists()
    assert [line["event_type"] for line in lines[:4]] == [
        "run-created",
        "run-started",
        "subtask-status",
        "run-event",
    ]
    assert lines[-1]["event_type"] == "run-failed"
    assert lines[-1]["error"] == "Synthetic failure"


def test_list_runs_returns_most_recent_first() -> None:
    store = AnalysisRunStore()
    first = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/one", branch="main")
    )
    second = store.create_run(
        AnalyzeRequest(repo_url="https://github.com/octocat/two", branch="dev")
    )

    reporter = RunProgressReporter(store, first.id)
    reporter.start()
    reporter.start_subtask("phase1", "parse_repo", "Parsing repository URL")

    runs = store.list_runs()

    assert [run.id for run in runs[:2]] == [first.id, second.id]
