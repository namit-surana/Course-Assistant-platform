import json
from pathlib import Path

import pytest

from src.github_agent.phase2.models.schemas import Task1GroupingOutput, Task2ResolutionOutput, UncertainFile
from src.github_agent.phase2.services.tree_analysis_service import TreeAnalysisService


@pytest.mark.asyncio
async def test_tree_analysis_service_saves_output_file(workspace_tmp_path: Path) -> None:
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
            "selected_file_count": 4,
        },
        "selected_files": [
            "README.md",
            "requirements.txt",
            "src/main.py",
            "docs/setup.md",
            "src/services/s3_service.py",
        ],
        "filtered_out_files": ["dist/app.js"],
        "documentation_files": [
            {"path": "README.md", "size": 100, "content": "# Hello"},
            {"path": "docs/setup.md", "size": 50, "content": "Setup"},
        ],
        "created_at": "2024-01-04T00:00:00Z",
    }
    repo_context_path = workspace_tmp_path / "octocat__Hello-World__repo_context.json"
    repo_context_path.write_text(json.dumps(repo_context_payload), encoding="utf-8")

    task1_output = Task1GroupingOutput(
        repo_type="backend_service",
        groups={
            "overview_docs": ["README.md", "docs/setup.md"],
            "build_dependencies": ["requirements.txt"],
            "backend": ["src/main.py"],
        },
        uncertain_files=[
            UncertainFile(
                path="src/services/s3_service.py",
                candidate_groups=["integrations", "backend"],
                reason="External service wrapper naming suggests integration work.",
            )
        ],
        unclassified_files=[],
        unknowns=[],
    )
    task2_output = Task2ResolutionOutput(
        resolved_groups={"integrations": ["src/services/s3_service.py"]},
        remaining_uncertain_files=[],
        remaining_unclassified_files=[],
        unknowns=["No tests detected in selected files"],
    )

    service = TreeAnalysisService(
        output_dir=workspace_tmp_path,
        tree_analysis_model="gemini/gemini-2.5-flash",
        phase2_runner=lambda analysis_input, model: (task1_output, task2_output),
    )

    result = await service.run_phase2_from_file(str(repo_context_path))

    output_path = workspace_tmp_path / "octocat__Hello-World__tree_analysis_plan.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert result.repo_type == "backend_service"
    assert output_path.exists()
    assert payload["plan"]["repo_type"] == "backend_service"
    assert payload["plan"]["groups"]["integrations"] == ["src/services/s3_service.py"]
    assert payload["analysis_input"]["documentation_previews"][0]["path"] == "README.md"


def test_detect_entrypoints_boosts_api_server_like_paths() -> None:
    service = TreeAnalysisService(
        output_dir=Path("."),
        tree_analysis_model="gemini/gemini-2.5-flash",
    )

    entrypoints = service._detect_entrypoints(
        ["webhook/server.js", "api_server.py", "converter.py"],
        allowed_suffixes={".py", ".js"},
    )

    assert entrypoints[0] == "api_server.py"
    assert "webhook/server.js" in entrypoints
