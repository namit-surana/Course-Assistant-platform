from pathlib import Path

import yaml


TASKS_CONFIG_PATH = Path("src/github_agent/phase3/crew/config/tasks.yaml")
AGENTS_CONFIG_PATH = Path("src/github_agent/phase3/crew/config/agents.yaml")


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_phase3_agents_define_five_specialists() -> None:
    agents = load_yaml(AGENTS_CONFIG_PATH)

    assert set(agents) == {
        "repo_intake_agent",
        "frontend_agent",
        "backend_agent",
        "integration_security_agent",
        "platform_quality_agent",
    }
    assert "synthesize specialist findings" in agents["repo_intake_agent"]["goal"]
    assert "browser-side runtime behavior" in agents["frontend_agent"]["goal"]
    assert "auth-sensitive boundaries" in agents["integration_security_agent"]["goal"]


def test_phase3_tasks_define_parallel_specialist_passes_and_final_synthesis() -> None:
    tasks = load_yaml(TASKS_CONFIG_PATH)

    assert tasks["repo_intake_task"]["agent"] == "repo_intake_agent"
    assert tasks["frontend_analysis_task"]["tools"] == ["fetch_repo_file_preview"]
    assert "Specialist analysis input:" in tasks["frontend_analysis_task"]["description"]
    assert "{specialist_input_json}" in tasks["frontend_analysis_task"]["description"]
    assert "Specialist analysis input:" in tasks["backend_analysis_task"]["description"]
    assert "{specialist_input_json}" in tasks["backend_analysis_task"]["description"]
    assert "Do not request the same chunk twice for the same file." in tasks["backend_analysis_task"]["description"]
    assert "Inspect at least two distinct assigned files when available before finalizing." in tasks["backend_analysis_task"]["description"]
    assert "Return at most 6 runtime_behavior items" in tasks["backend_analysis_task"]["description"]
    assert "Specialist analysis input:" in tasks["integration_security_task"]["description"]
    assert "{specialist_input_json}" in tasks["integration_security_task"]["description"]
    assert "Prioritize files that expose callback, secret, network, storage, deployment, or provider boundaries" in tasks["integration_security_task"]["description"]
    assert "Inspect at most 4 distinct assigned files" in tasks["integration_security_task"]["description"]
    assert "Inspect at most 2 chunks per file" in tasks["integration_security_task"]["description"]
    assert "Do not perform a full security audit." in tasks["integration_security_task"]["description"]
    assert "Do not repeat the repo overview, intake summary, or broad generic security advice" in tasks["integration_security_task"]["description"]
    assert "Specialist analysis input:" in tasks["platform_quality_task"]["description"]
    assert "{specialist_input_json}" in tasks["platform_quality_task"]["description"]
    assert "Do not restate repository architecture or produce a broad security review" in tasks["platform_quality_task"]["description"]
    assert "{frontend_summary_json}" in tasks["final_report_task"]["description"]
    assert "{backend_summary_json}" in tasks["final_report_task"]["description"]
    assert "{integration_security_summary_json}" in tasks["final_report_task"]["description"]
    assert "{platform_quality_summary_json}" in tasks["final_report_task"]["description"]
    assert "\"report_title\": \"...\"" in tasks["final_report_task"]["expected_output"]
