from __future__ import annotations

import logging
from pathlib import Path

from src.config.settings import Settings
from src.video_agent.crew.demo_video_crew import DemoVideoAnalysisCrew


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
use score Not_observable and explain briefly. Timestamps may be approximate or unknown.

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
      "score": "Exceeds|Meets|Partial|Missing|Not_observable",
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
) -> str:
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
    result = crew.kickoff(
        inputs={
            "video_path": str(video_path.resolve()),
            "assignment_title": assignment_title,
            "required_features": features_lines_for_task(required_features),
        }
    )
    output = str(result).strip()
    logger.info("Demo video crew finished for %s", video_path)
    return output


def features_lines_for_task(required_features: list[str] | None) -> str:
    if not required_features:
        return "- (none specified)"
    return "\n".join(f"- {item}" for item in required_features)
