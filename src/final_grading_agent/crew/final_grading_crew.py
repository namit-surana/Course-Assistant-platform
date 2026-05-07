from __future__ import annotations

from typing import Any

from src.final_grading_agent.models.schemas import FinalGradingOutput

try:
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.project import CrewBase, agent, crew, task
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "CrewAI is required for final grading analysis. Install dependencies from requirements.txt."
    ) from exc


@CrewBase
class FinalGradingCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, model: str, gemini_api_key: str | None) -> None:
        self.model = model
        self.gemini_api_key = gemini_api_key

    @agent
    def final_grading_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["final_grading_reviewer"],
            llm=LLM(model=self.model, api_key=self.gemini_api_key),
            verbose=False,
            allow_delegation=False,
        )

    @task
    def final_grading_task(self) -> Task:
        return Task(
            name="final_grading",
            config=self.tasks_config["final_grading_task"],
            output_pydantic=FinalGradingOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.final_grading_reviewer()],
            tasks=[self.final_grading_task()],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )


def run_final_grading(
    *,
    model: str,
    gemini_api_key: str | None,
    submission_context_json: str,
    criteria_config_json: str,
    repository_result_json: str,
    ppt_result_json: str,
    video_result_json: str,
) -> FinalGradingOutput:
    crew_driver = FinalGradingCrew(model=model, gemini_api_key=gemini_api_key)
    crew = crew_driver.crew()
    task_instance = crew_driver.final_grading_task()
    crew.kickoff(
        inputs={
            "submission_context_json": submission_context_json,
            "criteria_config_json": criteria_config_json,
            "repository_result_json": repository_result_json,
            "ppt_result_json": ppt_result_json,
            "video_result_json": video_result_json,
        }
    )

    if getattr(task_instance.output, "pydantic", None) is not None:
        return task_instance.output.pydantic
    if getattr(task_instance.output, "json_dict", None) is not None:
        return FinalGradingOutput.model_validate(task_instance.output.json_dict)
    if getattr(task_instance.output, "raw", None):
        return FinalGradingOutput.model_validate_json(task_instance.output.raw)
    raise RuntimeError("Final grading analysis did not produce structured output.")

