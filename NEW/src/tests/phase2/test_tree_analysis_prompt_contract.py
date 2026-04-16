from pathlib import Path

import yaml

from src.github_agent.phase1.models.schemas import RepoMetadata, TreeSummary
from src.github_agent.phase2.models.schemas import TreeAnalysisInput


TASKS_CONFIG_PATH = Path("src/github_agent/phase2/crew/config/tasks.yaml")


def load_task_configs() -> dict:
    return yaml.safe_load(TASKS_CONFIG_PATH.read_text(encoding="utf-8"))


def test_task1_prompt_contract_contains_critical_instructions() -> None:
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
            selected_file_count=4,
        ),
        selected_files=["README.md", "src/main.py"],
    )

    task_configs = load_task_configs()
    prompt = task_configs["task1_grouping"]["description"].format(
        analysis_input_json=analysis_input.model_dump_json(indent=2)
    )
    task_config = task_configs["task1_grouping"]["expected_output"]

    assert "Objective:" in prompt
    assert task_configs["task1_grouping"]["agent"] == "tree_analysis_agent"
    assert "Allowed component groups:" in prompt
    assert "Files that explain the project at a high level" in prompt
    assert "Files related to the user-facing application" in prompt
    assert "Files related to server-side request handling" in prompt
    assert "Files that define dependencies, packages, build tooling" in prompt
    assert "Files related to infrastructure provisioning, containerization, deployment, CI/CD" in prompt
    assert "Do not perform deep code review." in prompt
    assert "Do not invent files or paths." in prompt
    assert "Assign each file to the best-fit primary component" in prompt
    assert "Tie-break rules:" in prompt
    assert "runtime role over location" in prompt
    assert "specific component over generic component" in prompt
    assert "uncertain_files should include candidate_groups and a reason" in prompt
    assert task_config.strip().startswith("{")
    assert "\"repo_type\": \"backend_service | frontend_app | full_stack_app" in task_config


def test_task2_prompt_contract_contains_resolution_rules() -> None:
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
            selected_file_count=4,
        ),
        selected_files=["README.md", "src/services/s3.py"],
    )

    task_configs = load_task_configs()
    prompt = task_configs["task2_resolution"]["description"].format(
        analysis_input_json=analysis_input.model_dump_json(indent=2)
    )
    task_config = task_configs["task2_resolution"]["expected_output"]

    assert task_configs["task2_resolution"]["agent"] == "tree_analysis_agent"
    assert task_configs["task2_resolution"]["context"] == ["task1_grouping"]
    assert task_configs["task2_resolution"]["tools"] == ["fetch_uncertain_file_preview"]
    assert "Resolve the uncertain files and unclassified files from Task 1" in prompt
    assert "Only resolve files that Task 1 identified as uncertain or unclassified." in prompt
    assert "If Task 1 did not identify any uncertain files or unclassified files" in prompt
    assert "Use Task 1 context to identify which files were marked uncertain and which were left unclassified." in prompt
    assert "call the preview tool to inspect a bounded snippet" in prompt
    assert "Do not request the same chunk twice for the same file." in prompt
    assert "Once a file is clear enough to classify, move to the next unresolved file" in prompt
    assert "Fixed component taxonomy:" in prompt
    assert task_config.strip().startswith("{")
    assert "\"resolved_groups\": {" in task_config
    assert "\"remaining_unclassified_files\": [\"...\"]" in task_config
