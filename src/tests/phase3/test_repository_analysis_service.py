import json
import time
from pathlib import Path

import pytest

from src.github_agent.phase1.models.schemas import RepoMetadata, TreeSummary
from src.github_agent.phase2.models.schemas import EntrypointCandidates, SpecialistFocus, TreeAnalysisPlan
from src.github_agent.phase3.models.schemas import (
    FinalRepositoryAnalysis,
    RepoIntakeOutput,
    RepositoryAnalysisInput,
    RepositoryAnalysisRunResult,
    SpecialistAnalysisOutput,
)
from src.github_agent.phase3.services.repository_analysis_service import RepositoryAnalysisService
import src.github_agent.phase3.services.repository_analysis_service as repository_analysis_service_module


@pytest.mark.asyncio
async def test_repository_analysis_service_saves_json_and_markdown_outputs(workspace_tmp_path: Path) -> None:
    repo_context_payload = {
        "repo_url": "https://github.com/octocat/Hello-World",
        "owner": "octocat",
        "repo": "Hello-World",
        "branch": "main",
        "repo_metadata": {
            "full_name": "octocat/Hello-World",
            "description": "Example repo",
            "default_branch": "main",
            "language": "Python",
            "size": "10 KB",
            "stargazers_count": 1,
            "forks_count": 2,
            "open_issues_count": 0,
            "fork": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "pushed_at": "2024-01-03T00:00:00Z",
        },
        "tree_summary": {
            "total_items": 10,
            "total_blobs": 8,
            "total_trees": 2,
            "filtered_out_count": 1,
            "selected_file_count": 5,
        },
        "selected_files": [
            "README.md",
            "package.json",
            "src/main.py",
            "src/api/routes.py",
            "tests/test_api.py",
        ],
        "filtered_out_files": ["dist/app.js"],
        "documentation_files": [
            {"path": "README.md", "size": 100, "content": "# Hello"},
        ],
        "created_at": "2024-01-04T00:00:00Z",
    }
    tree_analysis_payload = {
        "repo_url": "https://github.com/octocat/Hello-World",
        "owner": "octocat",
        "repo": "Hello-World",
        "branch": "main",
        "source_repo_context_file": "outputs/octocat__Hello-World__repo_context.json",
        "analysis_input": {
            "repo_url": "https://github.com/octocat/Hello-World",
            "owner": "octocat",
            "repo": "Hello-World",
            "branch": "main",
            "repo_metadata": repo_context_payload["repo_metadata"],
            "tree_summary": repo_context_payload["tree_summary"],
            "selected_files": repo_context_payload["selected_files"],
            "documentation_previews": repo_context_payload["documentation_files"],
            "guaranteed_coverage_metadata": None,
        },
        "task1_output": {
            "repo_type": "backend_service",
            "groups": {
                "overview_docs": ["README.md"],
                "build_dependencies": ["package.json"],
                "backend": ["src/main.py", "src/api/routes.py"],
                "tests": ["tests/test_api.py"],
            },
            "uncertain_files": [],
            "unclassified_files": [],
            "unknowns": [],
        },
        "task2_output": {
            "resolved_groups": {},
            "remaining_uncertain_files": [],
            "remaining_unclassified_files": [],
            "unknowns": [],
        },
        "plan": {
            "repo_type": "backend_service",
            "confidence": 0.95,
            "important_paths": ["README.md", "src/main.py"],
            "entrypoint_candidates": {
                "backend": ["src/main.py"],
                "frontend": [],
            },
            "groups": {
                "overview_docs": ["README.md"],
                "build_dependencies": ["package.json"],
                "backend": ["src/main.py", "src/api/routes.py"],
                "tests": ["tests/test_api.py"],
            },
            "fetch_priority": ["README.md", "src/main.py", "src/api/routes.py"],
            "remaining_uncertain_files": [],
            "unclassified_files": [],
            "unknowns": [],
        },
        "created_at": "2024-01-04T00:00:00Z",
    }
    repo_context_path = workspace_tmp_path / "octocat__Hello-World__repo_context.json"
    tree_analysis_path = workspace_tmp_path / "octocat__Hello-World__tree_analysis_plan.json"
    repo_context_path.write_text(json.dumps(repo_context_payload), encoding="utf-8")
    tree_analysis_path.write_text(json.dumps(tree_analysis_payload), encoding="utf-8")

    specialist = SpecialistAnalysisOutput(
        applicable=True,
        summary="Relevant specialist pass.",
        runtime_behavior=["Handles incoming requests."],
        architecture_patterns=["Layered service architecture."],
        risks=["Coverage is concentrated around happy paths."],
        strengths=["Clear API module structure."],
        intelligent_questions=["How are background jobs triggered in production?"],
        evidence_paths=["src/main.py"],
    )
    run_result = RepositoryAnalysisRunResult(
        intake_output=RepoIntakeOutput(
            repo_summary="Backend API service.",
            main_capabilities=["Serve API requests"],
            stack_summary=["Python", "FastAPI"],
            maturity_signals=["Tests present"],
            architecture_hypotheses=["Layered backend service"],
            has_frontend=False,
            has_backend=True,
            has_integrations=False,
            has_platform_surface=True,
            focus_paths=["src/main.py", "src/api/routes.py"],
        ),
        frontend_output=SpecialistAnalysisOutput(applicable=False, summary="No frontend surface."),
        backend_output=specialist,
        integration_security_output=SpecialistAnalysisOutput(applicable=False, summary="No major integrations."),
        platform_quality_output=SpecialistAnalysisOutput(
            applicable=True,
            summary="Tests and tooling are present.",
            strengths=["Existing test suite"],
            evidence_paths=["tests/test_api.py"],
        ),
        final_analysis=FinalRepositoryAnalysis(
            report_title="Hello-World Repository Analysis",
            executive_summary="This repository is a focused backend service with clear structure.",
            repository_overview="The codebase centers on API request handling and supporting tests.",
            component_summary=["Backend API layer", "Test suite", "Project metadata"],
            runtime_behavior=["Requests enter through src/main.py and flow into route handlers."],
            architecture_patterns=["Layered service architecture"],
            risks_and_weaknesses=["Limited evidence of background processing."],
            quality_assessment="The repository shows healthy structure and some automated coverage.",
            strengths=["Clear module boundaries", "Tests present"],
            intelligent_questions=["How is deployment configured outside the repo?"],
            recommended_next_steps=["Review deployment config and secrets handling."],
            evidence_paths=["README.md", "src/main.py", "tests/test_api.py"],
        ),
    )

    service = RepositoryAnalysisService(
        output_dir=workspace_tmp_path,
        repository_analysis_model="gemini/gemini-2.5-flash",
        analysis_runner=lambda analysis_input, model, preview_fetcher=None: run_result,
    )

    analysis, output_path, markdown_path = await service.run_phase3_from_files_with_output(
        str(repo_context_path),
        str(tree_analysis_path),
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")

    assert analysis.report_title == "Hello-World Repository Analysis"
    assert output_path.exists()
    assert markdown_path.exists()
    assert payload["final_analysis"]["report_title"] == "Hello-World Repository Analysis"
    assert payload["markdown_report_file"] == markdown_path.as_posix()
    assert "# Hello-World Repository Analysis" in markdown
    assert "## Executive Summary" in markdown
    assert "- Repository: `octocat/Hello-World`" in markdown


def test_build_specialist_prompt_input_uses_scoped_context() -> None:
    analysis_input = RepositoryAnalysisInput(
        repo_url="https://github.com/octocat/Hello-World",
        owner="octocat",
        repo="Hello-World",
        branch="main",
        repo_metadata=RepoMetadata(
            full_name="octocat/Hello-World",
            description="Example repo",
            default_branch="main",
            language="Python",
            size="10 KB",
            stargazers_count=1,
            forks_count=2,
            open_issues_count=0,
            fork=False,
        ),
        tree_summary=TreeSummary(
            total_items=10,
            total_blobs=8,
            total_trees=2,
            filtered_out_count=1,
            selected_file_count=5,
        ),
        selected_files=["README.md", "src/main.py", "src/jobs/worker.py"],
        tree_analysis_plan=TreeAnalysisPlan(
            repo_type="backend_service",
            important_paths=["README.md", "src/main.py"],
            entrypoint_candidates=EntrypointCandidates(backend=["src/main.py"], frontend=[]),
            specialist_focus=[
                SpecialistFocus(
                    agent="backend_agent",
                    groups=["backend", "workers"],
                    assigned_paths=["src/main.py", "src/jobs/worker.py"],
                    reason="Derived from grouped components: backend, workers",
                )
            ],
        ),
    )
    intake_output = RepoIntakeOutput(
        repo_summary="Backend API service.",
        stack_summary=["Python", "FastAPI"],
        architecture_hypotheses=["Layered backend service"],
    )

    prompt_input = RepositoryAnalysisService._build_specialist_prompt_input(
        analysis_input,
        intake_output,
        "backend_agent",
    )

    assert prompt_input.repo_type == "backend_service"
    assert prompt_input.repo_summary == "Backend API service."
    assert prompt_input.important_paths == ["README.md", "src/main.py"]
    assert prompt_input.focus_groups == ["backend", "workers"]
    assert prompt_input.assigned_paths == ["src/main.py", "src/jobs/worker.py"]
    assert prompt_input.focus_reason == "Derived from grouped components: backend, workers"


def test_build_specialist_summary_limits_payload_size() -> None:
    output = SpecialistAnalysisOutput(
        applicable=True,
        summary="Backend review complete.",
        runtime_behavior=["a", "b", "c", "d"],
        architecture_patterns=["p1", "p2", "p3", "p4"],
        risks=["r1", "r2", "r3", "r4", "r5"],
        strengths=["s1", "s2", "s3", "s4"],
        intelligent_questions=["q1", "q2", "q3", "q4"],
        evidence_paths=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9"],
    )

    summary = RepositoryAnalysisService._build_specialist_summary(output)

    assert summary.top_runtime_behavior == ["a", "b", "c"]
    assert summary.top_architecture_patterns == ["p1", "p2", "p3"]
    assert summary.top_risks == ["r1", "r2", "r3", "r4"]
    assert summary.top_strengths == ["s1", "s2", "s3"]
    assert summary.top_questions == ["q1", "q2", "q3"]
    assert summary.evidence_paths == ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"]


def test_normalize_specialist_output_trims_and_deduplicates() -> None:
    output = SpecialistAnalysisOutput(
        applicable=True,
        summary="  " + ("very long summary " * 80),
        runtime_behavior=["same point", "same point", "b", "c", "d", "e", "f", "g"],
        architecture_patterns=["p1", "p2", "p3", "p4", "p5", "p6"],
        risks=["r1", "r2", "r3", "r4", "r5", "r6", "r7"],
        strengths=["s1", "s2", "s3", "s4", "s5", "s6"],
        intelligent_questions=["q1", "q2", "q3", "q4", "q5", "q6"],
        evidence_paths=["f1", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11"],
    )

    normalized = RepositoryAnalysisService._normalize_specialist_output(output)

    assert len(normalized.summary) <= 700
    assert normalized.runtime_behavior == ["same point", "b", "c", "d", "e", "f"]
    assert normalized.architecture_patterns == ["p1", "p2", "p3", "p4", "p5"]
    assert normalized.risks == ["r1", "r2", "r3", "r4", "r5", "r6"]
    assert normalized.strengths == ["s1", "s2", "s3", "s4", "s5"]
    assert normalized.intelligent_questions == ["q1", "q2", "q3", "q4", "q5"]
    assert normalized.evidence_paths == ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10"]


@pytest.mark.asyncio
async def test_phase3_specialist_reviews_run_in_parallel(monkeypatch: pytest.MonkeyPatch, workspace_tmp_path: Path) -> None:
    analysis_input = RepositoryAnalysisInput(
        repo_url="https://github.com/octocat/Hello-World",
        owner="octocat",
        repo="Hello-World",
        branch="main",
        repo_metadata=RepoMetadata(
            full_name="octocat/Hello-World",
            description="Example repo",
            default_branch="main",
            language="Python",
            size="10 KB",
            stargazers_count=1,
            forks_count=2,
            open_issues_count=0,
            fork=False,
        ),
        tree_summary=TreeSummary(
            total_items=10,
            total_blobs=8,
            total_trees=2,
            filtered_out_count=1,
            selected_file_count=5,
        ),
        selected_files=[
            "README.md",
            "src/ui/App.tsx",
            "src/main.py",
            "tests/test_api.py",
            ".github/workflows/ci.yml",
        ],
        tree_analysis_plan=TreeAnalysisPlan(
            repo_type="full_stack_app",
            important_paths=["README.md", "src/main.py", "src/ui/App.tsx"],
            entrypoint_candidates=EntrypointCandidates(backend=["src/main.py"], frontend=["src/ui/App.tsx"]),
            specialist_focus=[
                SpecialistFocus(
                    agent="frontend_agent",
                    groups=["frontend"],
                    assigned_paths=["src/ui/App.tsx"],
                    reason="Frontend files grouped in tree analysis.",
                ),
                SpecialistFocus(
                    agent="backend_agent",
                    groups=["backend"],
                    assigned_paths=["src/main.py"],
                    reason="Backend files grouped in tree analysis.",
                ),
                SpecialistFocus(
                    agent="integration_security_agent",
                    groups=["infra_deployment"],
                    assigned_paths=[".github/workflows/ci.yml"],
                    reason="Infra-related files grouped in tree analysis.",
                ),
                SpecialistFocus(
                    agent="platform_quality_agent",
                    groups=["tests"],
                    assigned_paths=["tests/test_api.py"],
                    reason="Test files grouped in tree analysis.",
                ),
            ],
        ),
    )
    intake_output = RepoIntakeOutput(
        repo_summary="Full-stack application.",
        stack_summary=["Python", "React"],
        architecture_hypotheses=["UI + API application"],
    )
    specialist_output = SpecialistAnalysisOutput(applicable=True, summary="done")
    final_analysis = FinalRepositoryAnalysis(
        report_title="Parallel Test",
        executive_summary="ok",
        repository_overview="ok",
        quality_assessment="ok",
    )

    monkeypatch.setattr(
        repository_analysis_service_module,
        "run_repo_intake_analysis",
        lambda analysis_input, model, run_reporter=None: intake_output,
    )

    call_times: dict[str, tuple[float, float]] = {}

    def make_runner(name: str):
        def runner(*args, **kwargs):
            start = time.perf_counter()
            time.sleep(0.2)
            end = time.perf_counter()
            call_times[name] = (start, end)
            return specialist_output

        return runner

    monkeypatch.setattr(repository_analysis_service_module, "run_frontend_review", make_runner("frontend"))
    monkeypatch.setattr(repository_analysis_service_module, "run_backend_review", make_runner("backend"))
    monkeypatch.setattr(
        repository_analysis_service_module,
        "run_integration_security_review",
        make_runner("integration"),
    )
    monkeypatch.setattr(repository_analysis_service_module, "run_platform_quality_review", make_runner("quality"))
    monkeypatch.setattr(
        repository_analysis_service_module,
        "run_final_report",
        lambda *args, **kwargs: final_analysis,
    )

    service = RepositoryAnalysisService(
        output_dir=workspace_tmp_path,
        repository_analysis_model="gemini/gemini-2.5-flash",
    )

    started = time.perf_counter()
    result = await service._run_default_sequence(
        analysis_input=analysis_input,
        preview_fetcher=None,
        progress_callback=None,
        run_reporter=None,
    )
    elapsed = time.perf_counter() - started

    assert result.final_analysis.report_title == "Parallel Test"
    assert set(call_times) == {"frontend", "backend", "integration", "quality"}
    assert elapsed < 0.55
    earliest_end = min(end for _, end in call_times.values())
    latest_start = max(start for start, _ in call_times.values())
    assert latest_start < earliest_end
