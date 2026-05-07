from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import Settings
from src.video_agent.crew.demo_video_crew import DemoVideoAnalysisCrew
from src.video_agent.models.schemas import DemoVideoAnalysisOutput


logger = logging.getLogger(__name__)


def _rubric_path() -> Path:
    return Path(__file__).resolve().parent.parent / "knowledge" / "default_rubric.md"


def load_default_rubric() -> str:
    return _rubric_path().read_text(encoding="utf-8")


def build_analysis_prompt(
    *,
    assignment_title: str,
    required_features: list[str] | None,
) -> str:
    rubric = load_default_rubric()
    features_lines = (
        "\n".join(f"- {item}" for item in required_features) if required_features else "- (none specified)"
    )
    return f"""You are analyzing a student demo video for instructors.

Use ONLY what is visible or audible in the video. If something cannot be verified from the recording,
use score 0 and explain briefly that it was not observable. Timestamps may be approximate or unknown.

RUBRIC:
{rubric}

ASSIGNMENT TITLE:
{assignment_title}

REQUIRED FEATURES CHECKLIST:
{features_lines}

Return ONLY valid JSON (no markdown code fences, no prose outside JSON). Use exactly this shape:
{{
  "summary": "<2-4 sentences>",
  "rubric": [
    {{
      "id": "A1",
      "score": <number 0-5>,
      "evidence": "<what you saw or heard>",
      "timestamps": "<approximate or unknown>"
    }}
  ],
  "feature_coverage": [
    {{
      "feature": "<text>",
      "status": "shown|partial|not_shown|not_applicable",
      "evidence": "<brief>"
    }}
  ],
  "gaps_and_risks": ["<string>"],
  "limitations": "<model or visibility caveats>"
}}

Include one rubric object for every rubric id from A1 through F2 that appears in the rubric markdown.
Include one feature_coverage object for each required feature line (or a single not_applicable entry if none).
"""


def run_demo_video_analysis(
    video_path: Path,
    assignment_title: str,
    required_features: list[str] | None,
    settings: Settings,
) -> tuple[str, dict]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    prompt = build_analysis_prompt(
        assignment_title=assignment_title,
        required_features=required_features,
    )
    crew_driver = DemoVideoAnalysisCrew(
        model=settings.video_analysis_model,
        gemini_api_key=settings.GEMINI_API_KEY,
        analysis_prompt=prompt,
    )
    crew = crew_driver.crew()
    task_instance = crew_driver.demo_video_analysis_task()
    crew.kickoff(
        inputs={
            "video_path": str(video_path.resolve()),
            "assignment_title": assignment_title,
            "required_features": features_lines_for_task(required_features),
        }
    )
    output_model: DemoVideoAnalysisOutput
    if getattr(task_instance.output, "pydantic", None) is not None:
        output_model = task_instance.output.pydantic
    elif getattr(task_instance.output, "json_dict", None) is not None:
        output_model = DemoVideoAnalysisOutput.model_validate(task_instance.output.json_dict)
    elif getattr(task_instance.output, "raw", None):
        output_model = DemoVideoAnalysisOutput.model_validate_json(task_instance.output.raw)
    else:
        raise RuntimeError("Demo video analysis did not produce structured output.")

    raw_output = output_model.model_dump_json()
    parsed = output_model.model_dump(mode="json")
    logger.info("Demo video crew finished for %s", video_path)
    return raw_output, parsed


def features_lines_for_task(required_features: list[str] | None) -> str:
    if not required_features:
        return "- (none specified)"
    return "\n".join(f"- {item}" for item in required_features)
