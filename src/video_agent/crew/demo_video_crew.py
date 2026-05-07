from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.video_agent.services.gemini_video import analyze_video_file
from src.video_agent.models.schemas import DemoVideoAnalysisOutput
from src.video_agent.utils import extract_json_object


try:
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.project import CrewBase, agent, crew, task, tool
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "CrewAI is required for demo video analysis. Install dependencies from requirements.txt."
    ) from exc


@CrewBase
class DemoVideoAnalysisCrew:
    """Single-agent crew: tool performs Gemini multimodal analysis."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, model: str, gemini_api_key: str | None, analysis_prompt: str) -> None:
        self.model = model
        self.gemini_api_key = gemini_api_key
        self.analysis_prompt = analysis_prompt

    @agent
    def demo_video_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["demo_video_analyst"],
            llm=LLM(model=self.model, api_key=self.gemini_api_key),
            verbose=False,
            allow_delegation=False,
        )

    @task
    def demo_video_analysis_task(self) -> Task:
        return Task(
            name="demo_video_analysis",
            config=self.tasks_config["demo_video_analysis_task"],
            output_pydantic=DemoVideoAnalysisOutput,
        )

    @tool
    def analyze_demo_video(self) -> Any:
        outer = self

        class VideoPathSchema(BaseModel):
            video_path: str = Field(..., description="Absolute filesystem path to the demo video.")

        try:
            from crewai.tools import BaseTool
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("CrewAI tool support is required for demo video analysis.") from exc

        class AnalyzeDemoVideoTool(BaseTool):
            name: str = "analyze_demo_video"
            description: str = (
                "Uploads the demo video to Gemini, applies the rubric prompt, and returns a JSON object. "
                "Call exactly once with the path from the task."
            )
            args_schema: type[BaseModel] = VideoPathSchema

            def _run(self, video_path: str) -> dict[str, Any]:
                from src.config.settings import get_settings

                settings = get_settings()
                api_key = outer.gemini_api_key or settings.GEMINI_API_KEY
                raw = analyze_video_file(
                    video_path=video_path,
                    prompt=outer.analysis_prompt,
                    model=settings.video_analysis_model,
                    api_key=api_key,
                )
                return extract_json_object(raw)

        return AnalyzeDemoVideoTool()

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.demo_video_analyst()],
            tasks=[self.demo_video_analysis_task()],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
