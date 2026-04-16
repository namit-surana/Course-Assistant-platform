import json
from pathlib import Path

from src.github_agent.phase1.models.schemas import DocumentationFile, FilteredRepoContext, RepoMetadata, TreeItem
from src.github_agent.phase1.services.context_builder import ContextBuilder


def test_build_and_save_context(workspace_tmp_path: Path) -> None:
    builder = ContextBuilder(output_dir=workspace_tmp_path)
    metadata = RepoMetadata(
        full_name="octocat/Hello-World",
        description="Sample repo",
        default_branch="main",
        language="Python",
        stargazers_count=10,
        forks_count=2,
        open_issues_count=1,
    )
    tree_items = [
        TreeItem(path="README.md", type="blob", size=100),
        TreeItem(path="src", type="tree"),
        TreeItem(path="src/main.py", type="blob", size=200),
    ]
    filtered_context = FilteredRepoContext(
        selected_files=[
            TreeItem(path="README.md", type="blob", size=100),
            TreeItem(path="src/main.py", type="blob", size=200),
        ],
        excluded_files=[],
        selected_paths=["README.md", "src/main.py"],
        filtered_out_paths=[],
        filtered_out_count=0,
        selected_file_count=2,
        exclusion_reasons={},
    )

    artifact = builder.build_context(
        repo_url="https://github.com/octocat/Hello-World",
        owner="octocat",
        repo="Hello-World",
        branch="main",
        repo_metadata=metadata,
        tree_items=tree_items,
        filtered_context=filtered_context,
        documentation_files=[
            DocumentationFile(path="README.md", size=100, content="# Hello World"),
        ],
    )
    output_path = builder.save_context(artifact)
    chunk_index = builder.build_chunk_index(
        repo_url="https://github.com/octocat/Hello-World",
        owner="octocat",
        repo="Hello-World",
        branch="main",
        selected_files=[
            DocumentationFile(path="README.md", size=100, content="# Hello World"),
            DocumentationFile(path="src/main.py", size=200, content="print('hi')\nprint('bye')"),
        ],
    )
    chunk_index_path = builder.save_chunk_index(chunk_index)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    chunk_payload = json.loads(chunk_index_path.read_text(encoding="utf-8"))
    assert output_path.name == "octocat__Hello-World__repo_context.json"
    assert chunk_index_path.name == "octocat__Hello-World__repo_chunk_index.json"
    assert payload["repo_url"] == "https://github.com/octocat/Hello-World"
    assert payload["tree_summary"]["total_items"] == 3
    assert payload["tree_summary"]["total_blobs"] == 2
    assert payload["tree_summary"]["total_trees"] == 1
    assert payload["selected_files"] == ["README.md", "src/main.py"]
    assert payload["filtered_out_files"] == []
    assert payload["documentation_files"][0]["path"] == "README.md"
    assert payload["documentation_files"][0]["content"] == "# Hello World"
    assert chunk_payload["selected_file_count"] == 2
    assert chunk_payload["files"][1]["chunks"][0]["start_line"] == 1
    assert chunk_payload["files"][1]["chunks"][0]["end_line"] == 2
