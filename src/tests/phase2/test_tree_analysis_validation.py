from pathlib import Path

import pytest

from src.github_agent.phase1.models.schemas import RepoMetadata, TreeSummary
from src.github_agent.phase2.models.schemas import Task1GroupingOutput, Task2ResolutionOutput, TreeAnalysisInput
from src.github_agent.phase2.services.tree_analysis_service import TreeAnalysisParserError, TreeAnalysisService


def test_task1_parser_accepts_invented_files_without_custom_validation() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    raw_output = {
        "repo_type": "backend_service",
        "groups": {
            "overview_docs": ["README.md"],
            "backend": ["missing.py"],
        },
        "uncertain_files": [],
        "unclassified_files": [],
        "unknowns": [],
    }

    result = service.parse_task1_output(raw_output)

    assert result.groups["backend"] == ["missing.py"]


def test_task1_parser_rejects_invalid_component_name() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    raw_output = {
        "repo_type": "backend_service",
        "groups": {"random_bucket": ["src/main.py"]},
        "uncertain_files": [],
        "unclassified_files": [],
        "unknowns": [],
    }

    with pytest.raises(TreeAnalysisParserError, match="schema validation"):
        service.parse_task1_output(raw_output)


def test_task2_parser_accepts_non_uncertain_resolution_without_custom_validation() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    raw_output = {
        "resolved_groups": {"integrations": ["src/main.py"]},
        "remaining_uncertain_files": [],
        "remaining_unclassified_files": [],
        "unknowns": [],
    }

    result = service.parse_task2_output(raw_output)

    assert result.resolved_groups["integrations"] == ["src/main.py"]


def test_task1_parser_preserves_raw_output_without_custom_normalization() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    raw_output = {
        "repo_type": "backend_service",
        "groups": {
            "overview_docs": ["README.md", "README.md"],
            "backend": ["src/../src/main.py"],
        },
        "uncertain_files": [
            {
                "path": "src/../src/worker.py",
                "candidate_groups": ["workers", "backend"],
                "reason": " Could be a worker entrypoint. ",
            }
        ],
        "unclassified_files": ["README.md", "README.md"],
        "unknowns": ["", "Need test coverage", "Need test coverage"],
    }

    result = service.parse_task1_output(raw_output)

    assert result.groups["overview_docs"] == ["README.md", "README.md"]
    assert result.groups["backend"] == ["src/../src/main.py"]
    assert result.uncertain_files[0].path == "src/../src/worker.py"
    assert result.uncertain_files[0].reason == " Could be a worker entrypoint. "
    assert result.unclassified_files == ["README.md", "README.md"]
    assert result.unknowns == ["", "Need test coverage", "Need test coverage"]


def test_task2_parser_preserves_raw_output_without_custom_normalization() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    raw_output = {
        "resolved_groups": {"integrations": ["src/../src/services/s3.py", "src/services/s3.py"]},
        "remaining_uncertain_files": [
            {
                "path": "src/../src/worker.py",
                "candidate_groups": ["workers", "backend"],
                "reason": "Still ambiguous after preview.",
            }
        ],
        "remaining_unclassified_files": ["mystery.bin", "mystery.bin"],
        "unknowns": ["", "No tests detected", "No tests detected"],
    }

    result = service.parse_task2_output(raw_output)

    assert result.resolved_groups["integrations"] == ["src/../src/services/s3.py", "src/services/s3.py"]
    assert result.remaining_uncertain_files[0].path == "src/../src/worker.py"
    assert result.remaining_unclassified_files == ["mystery.bin", "mystery.bin"]
    assert result.unknowns == ["", "No tests detected", "No tests detected"]


def test_final_plan_derives_specialist_focus_from_grouped_components() -> None:
    service = TreeAnalysisService(output_dir=Path("."), tree_analysis_model="gemini/gemini-2.5-flash")
    analysis_input = TreeAnalysisInput(
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
        selected_files=["README.md", "src/main.py", "src/jobs/worker.py", "tests/test_api.py", "package.json"],
    )
    task1_output = Task1GroupingOutput(
        repo_type="backend_service",
        groups={
            "overview_docs": ["README.md"],
            "backend": ["src/main.py"],
            "workers": ["src/jobs/worker.py"],
            "tests": ["tests/test_api.py"],
            "build_dependencies": ["package.json"],
        },
    )
    task2_output = Task2ResolutionOutput()

    plan = service.build_final_plan(analysis_input, task1_output, task2_output)

    focus_by_agent = {item.agent: item for item in plan.specialist_focus}

    assert focus_by_agent["backend_agent"].groups == ["backend", "workers"]
    assert focus_by_agent["backend_agent"].assigned_paths == ["src/main.py", "src/jobs/worker.py"]
    assert focus_by_agent["platform_quality_agent"].groups == ["tests", "build_dependencies"]
    assert focus_by_agent["platform_quality_agent"].assigned_paths == ["package.json", "tests/test_api.py"]
    assert "frontend_agent" not in focus_by_agent
