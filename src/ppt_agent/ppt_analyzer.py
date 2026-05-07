from typing import Any

from src.config.settings import get_settings
from src.ppt_agent.core import BUILTIN_PPT_RUBRIC_CRITERIA, builtin_ppt_rubric_by_category
from src.ppt_agent.crew.ppt_crew import run_ppt_analysis

settings = get_settings()

def analyze_ppt(
    file_path: str,
    rubric_criteria: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Analyze PPT/PDF content using CrewAI + Gemini.

    Pass a non-empty ``rubric_criteria`` only for ad-hoc tools (e.g. /analyze-ppt). The worker omits
    this so :data:`BUILTIN_PPT_RUBRIC_CRITERIA` is always used.
    """
    try:
        # For backward compatibility, we keep the function signature, but the new implementation
        # uses the CrewAI "project" pattern (CrewBase + YAML + tools + structured output).
        if rubric_criteria:
            # Ad-hoc rubric injection is not supported in the project-style crew yet.
            # Fall back to builtin rubric to keep worker behavior deterministic.
            pass
        output = run_ppt_analysis(
            file_path,
            model="gemini/gemini-2.5-flash-lite",
            gemini_api_key=settings.GEMINI_API_KEY,
        )
        # `run_ppt_analysis` already returns a complete, schema-validated output (all A1–F2 present).
        return output.model_dump(mode="json")

    except Exception as exc:
        return {
            "criteria_scores": [],
            "ppt_summary": "",
            "error": f"Analysis failed: {str(exc)}",
        }
