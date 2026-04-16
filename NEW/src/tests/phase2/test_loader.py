import json

from pathlib import Path

from src.github_agent.phase2.services.loader import Phase2Loader


def test_phase2_loader_validates_phase1_artifact(workspace_tmp_path: Path) -> None:
    payload = {
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
            "selected_file_count": 7,
        },
        "selected_files": ["README.md", "src/main.py"],
        "filtered_out_files": ["dist/app.js"],
        "documentation_files": [{"path": "README.md", "size": 100, "content": "# Hello"}],
        "created_at": "2024-01-04T00:00:00Z",
    }
    path = workspace_tmp_path / "repo_context.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = Phase2Loader().load_phase1_artifact(path)

    assert result.owner == "octocat"
    assert result.selected_files == ["README.md", "src/main.py"]
    assert result.documentation_files[0].path == "README.md"
