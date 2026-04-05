import json
import re
from typing import Any

from crewai import Agent, Crew, LLM, Task
from pptx import Presentation

from app.config import get_settings

settings = get_settings()


def extract_ppt_text(ppt_path: str) -> str:
    """Extract all text content from a PowerPoint file."""
    prs = Presentation(ppt_path)
    slides_text: list[str] = []

    for i, slide in enumerate(prs.slides, start=1):
        slide_texts: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text = shape.text.strip()
                if text:
                    slide_texts.append(text)

        if slide_texts:
            slides_text.append(f"[Slide {i}]\n" + "\n".join(slide_texts))

    return "\n\n".join(slides_text)


def _extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract JSON safely from CrewAI/LLM output."""
    cleaned = text.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON returned by model: {exc}") from exc

    raise ValueError("No valid JSON object found in analyzer response.")


def _normalize_scores(result: dict[str, Any], rubric_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """Clamp scores so they stay within each rubric criterion's max_score."""
    max_score_map = {
        criterion["category"]: float(criterion["max_score"])
        for criterion in rubric_criteria
    }

    for item in result.get("criteria_scores", []):
        category = item.get("category")
        raw_score = item.get("score", 0)

        try:
            numeric_score = float(raw_score)
        except (TypeError, ValueError):
            numeric_score = 0.0

        max_allowed = max_score_map.get(category, numeric_score)
        item["score"] = max(0.0, min(numeric_score, max_allowed))

    return result


def analyze_ppt(ppt_path: str, rubric_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze PPT content against rubric criteria using CrewAI."""
    slide_text = extract_ppt_text(ppt_path)

    if not slide_text.strip():
        return {
            "criteria_scores": [],
            "ppt_summary": "No readable text was found in the presentation.",
            "error": "Empty presentation content",
        }

    criteria_text = "\n".join(
        [
            f"- {criterion['category']} (max {criterion['max_score']} pts): {criterion['description']}"
            for criterion in rubric_criteria
        ]
    )

    llm = LLM(
        model="gemini/gemini-1.5-pro",
        api_key=settings.GEMINI_API_KEY,
    )

    ppt_analyzer_agent = Agent(
        role="PPT Analyzer",
        goal="Evaluate presentation slides against a rubric and return strict JSON output.",
        backstory=(
            "You are an academic presentation evaluator. "
            "You score fairly, justify each score briefly, and always return valid JSON."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    prompt = f"""
You are an academic evaluator.

Analyze the following presentation slides against the given rubric.

RUBRIC CRITERIA:
{criteria_text}

PRESENTATION CONTENT:
{slide_text}

Instructions:
- Evaluate each rubric criterion separately.
- Score must be between 0 and that criterion's max_score.
- Give a brief comment for each criterion.
- Give an overall 2-3 sentence summary.
- Return ONLY valid JSON.
- Do not wrap JSON in markdown.

Return exactly this structure:
{{
  "criteria_scores": [
    {{
      "category": "<criterion name>",
      "score": <number>,
      "comment": "<explanation>"
    }}
  ],
  "ppt_summary": "<overall 2-3 sentence summary of the presentation>"
}}
"""

    analyze_task = Task(
        description=prompt,
        expected_output="A valid JSON object with criterion-wise scores and PPT summary.",
        agent=ppt_analyzer_agent,
    )

    crew = Crew(
        agents=[ppt_analyzer_agent],
        tasks=[analyze_task],
        verbose=True,
    )

    try:
        result = crew.kickoff()
        parsed = _extract_json_from_text(str(result))
        normalized = _normalize_scores(parsed, rubric_criteria)
        return normalized
    except Exception as exc:
        return {
            "criteria_scores": [],
            "ppt_summary": "",
            "error": f"PPT analysis failed: {str(exc)}",
        }
