from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.ppt_agent.models.schemas import PptAnalysisOutput, PptCriterionScore
from src.ppt_agent.core import BUILTIN_PPT_RUBRIC_CRITERIA, extract_document_text, load_default_ppt_rubric

try:
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.project import CrewBase, agent, crew, task, tool
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("CrewAI is required for PPT analysis. Install dependencies from requirements.txt.") from exc


class DocumentPathSchema(BaseModel):
    file_path: str = Field(..., description="Absolute filesystem path to a .pptx or .pdf file.")


@CrewBase
class PptAnalysisCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def __init__(self, model: str, gemini_api_key: str | None) -> None:
        self.model = model
        self.gemini_api_key = gemini_api_key

    @agent
    def ppt_rubric_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["ppt_rubric_analyst"],
            llm=LLM(model=self.model, api_key=self.gemini_api_key),
            verbose=False,
            allow_delegation=False,
        )

    @tool
    def extract_document_text(self) -> Any:
        outer = self

        try:
            from crewai.tools import BaseTool
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("CrewAI tool support is required for PPT analysis.") from exc

        class ExtractDocumentTextTool(BaseTool):
            name: str = "extract_document_text"
            description: str = "Extract readable text from a .pptx or .pdf given a local file path."
            args_schema: type[BaseModel] = DocumentPathSchema

            def _run(self, file_path: str) -> dict[str, str]:
                # Keep return type JSON-serializable and explicit.
                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(f"Document not found: {file_path}")
                extracted = extract_document_text(file_path)
                return {"extracted_text": extracted}

        return ExtractDocumentTextTool()

    @task
    def ppt_analysis_task(self) -> Task:
        return Task(
            name="ppt_analysis",
            config=self.tasks_config["ppt_analysis_task"],
            output_pydantic=PptAnalysisOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.ppt_rubric_analyst()],
            tasks=[self.ppt_analysis_task()],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )


def run_ppt_analysis(file_path: str, *, model: str, gemini_api_key: str | None) -> PptAnalysisOutput:
    crew_driver = PptAnalysisCrew(model=model, gemini_api_key=gemini_api_key)
    crew = crew_driver.crew()
    task_instance = crew_driver.ppt_analysis_task()
    criteria_text = "\n".join(
        [
            f"- {item['category']} (max {item['max_score']} pts): {item['description']}"
            for item in BUILTIN_PPT_RUBRIC_CRITERIA
        ]
    )
    crew.kickoff(
        inputs={
            "file_path": str(Path(file_path).resolve()),
            "rubric_guidance": load_default_ppt_rubric(),
            "criteria_text": criteria_text,
        }
    )

    output_model: PptAnalysisOutput
    if getattr(task_instance.output, "pydantic", None) is not None:
        output_model = task_instance.output.pydantic
    elif getattr(task_instance.output, "json_dict", None) is not None:
        output_model = PptAnalysisOutput.model_validate(task_instance.output.json_dict)
    elif getattr(task_instance.output, "raw", None):
        output_model = PptAnalysisOutput.model_validate_json(task_instance.output.raw)
    else:
        raise RuntimeError("PPT analysis did not produce structured output.")

    # Enforce a complete A1–F2 output contract, so downstream code never needs legacy normalization.
    by_category = {row.category: row for row in output_model.criteria_scores}
    completed_rows: list[PptCriterionScore] = []
    for rubric_item in BUILTIN_PPT_RUBRIC_CRITERIA:
        category = str(rubric_item["category"])
        max_score = float(rubric_item["max_score"])
        matched = by_category.get(category)
        if matched is None:
            completed_rows.append(
                PptCriterionScore(
                    category=category,
                    score=0.0,
                    comment="No evaluation returned for this criterion.",
                )
            )
            continue
        score = float(matched.score or 0.0)
        score = max(0.0, min(score, max_score))
        completed_rows.append(
            PptCriterionScore(
                category=category,
                score=score,
                comment=str(matched.comment or "").strip(),
            )
        )

    summary = str(output_model.ppt_summary or "").strip()
    return PptAnalysisOutput(criteria_scores=completed_rows, ppt_summary=summary, error=output_model.error)

