import json
import re
from typing import Any

import fitz  # PyMuPDF
from crewai import Agent, Crew, LLM, Task
from pptx import Presentation

from src.config.settings import get_settings

settings = get_settings()


def extract_ppt_text(file_path: str) -> str:
    """Extract readable text from a .pptx file."""
    presentation = Presentation(file_path)
    slides_text: list[str] = []

    for index, slide in enumerate(presentation.slides, start=1):
        slide_parts: list[str] = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                text = shape.text.strip()
                if text:
                    slide_parts.append(text)

        if slide_parts:
            slides_text.append(f"[Slide {index}]\n" + "\n".join(slide_parts))

    return "\n\n".join(slides_text)


def extract_pdf_text(file_path: str) -> str:
    """Extract readable text from a .pdf file."""
    doc = fitz.open(file_path)
    pages_text: list[str] = []

    for index, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if text:
            pages_text.append(f"[Page {index}]\n{text}")

    doc.close()
    return "\n\n".join(pages_text)


def extract_document_text(file_path: str) -> str:
    """Extract text from supported document formats."""
    lower_path = file_path.lower()

    if lower_path.endswith(".pptx"):
        return extract_ppt_text(file_path)

    if lower_path.endswith(".pdf"):
        return extract_pdf_text(file_path)

    raise ValueError("Only .pptx and .pdf files are supported")


def _extract_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(0))

    raise ValueError("No valid JSON object found in model response")


def _normalize_scores(
    result: dict[str, Any], rubric_criteria: list[dict[str, Any]]
) -> dict[str, Any]:
    normalized_scores: list[dict[str, Any]] = []

    for rubric_item in rubric_criteria:
        category = rubric_item["category"]
        max_score = float(rubric_item["max_score"])

        matched = None
        for score_item in result.get("criteria_scores", []):
            if score_item.get("category") == category:
                matched = score_item
                break

        if matched is None:
            normalized_scores.append(
                {
                    "category": category,
                    "score": 0.0,
                    "comment": "No evaluation returned for this criterion.",
                }
            )
            continue

        try:
            numeric_score = float(matched.get("score", 0))
        except (TypeError, ValueError):
            numeric_score = 0.0

        numeric_score = max(0.0, min(numeric_score, max_score))

        normalized_scores.append(
            {
                "category": category,
                "score": numeric_score,
                "comment": str(matched.get("comment", "")).strip(),
            }
        )

    result["criteria_scores"] = normalized_scores
    result["ppt_summary"] = str(result.get("ppt_summary", "")).strip()

    return result


def analyze_ppt(file_path: str, rubric_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyze PPT/PDF content against rubric criteria using CrewAI + Gemini.
    Supports .pptx and .pdf files.
    """
    try:
        document_text = extract_document_text(file_path)

        if not document_text.strip():
            return {
                "criteria_scores": [],
                "ppt_summary": "No readable text was found in the file.",
                "error": "Empty file content",
            }

        criteria_text = "\n".join(
            [
                f"- {item['category']} (max {item['max_score']} pts): {item['description']}"
                for item in rubric_criteria
            ]
        )

        llm = LLM(
            model="gemini/gemini-2.5-flash-lite",
            api_key=settings.GEMINI_API_KEY,
        )

        analyzer_agent = Agent(
            role="Presentation Analyzer",
            goal="Evaluate presentation or document content against rubric criteria and return strict JSON output.",
            backstory=(
                "You are an academic evaluator. You score each rubric criterion carefully, "
                "justify each score briefly, and always return valid JSON only."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        prompt = f"""
You are evaluating an academic presentation/document.

RUBRIC CRITERIA:
{criteria_text}

DOCUMENT CONTENT:
{document_text}

Instructions:
- Evaluate each rubric criterion separately.
- Score each criterion from 0 up to that criterion's max_score.
- Give a short but clear explanation for each criterion.
- Give an overall 2-3 sentence summary.
- Return ONLY valid JSON.
- Do not include markdown.
- Do not include any extra text before or after the JSON.

Return exactly this JSON structure:
{{
  "criteria_scores": [
    {{
      "category": "<criterion name>",
      "score": <number>,
      "comment": "<brief explanation>"
    }}
  ],
  "ppt_summary": "<overall 2-3 sentence summary>"
}}
"""

        analyze_task = Task(
            description=prompt,
            expected_output="A valid JSON object with criterion-wise scores and a summary.",
            agent=analyzer_agent,
        )

        crew = Crew(
            agents=[analyzer_agent],
            tasks=[analyze_task],
            verbose=False,
        )

        result = crew.kickoff()
        parsed = _extract_json_from_text(str(result))
        return _normalize_scores(parsed, rubric_criteria)

    except Exception as exc:
        return {
            "criteria_scores": [],
            "ppt_summary": "",
            "error": f"Analysis failed: {str(exc)}",
        }
