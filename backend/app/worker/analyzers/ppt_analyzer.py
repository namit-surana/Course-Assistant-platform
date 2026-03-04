from pptx import Presentation
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)


def extract_ppt_text(ppt_path: str) -> str:
    """Extract all text content from a PowerPoint file."""
    prs = Presentation(ppt_path)
    slides_text = []
    for i, slide in enumerate(prs.slides):
        slide_texts = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_texts.append(shape.text.strip())
        if slide_texts:
            slides_text.append(f"[Slide {i + 1}]\n" + "\n".join(slide_texts))
    return "\n\n".join(slides_text)


def analyze_ppt(ppt_path: str, rubric_criteria: list) -> dict:
    """Analyze PPT content against rubric criteria using Gemini."""
    slide_text = extract_ppt_text(ppt_path)
    criteria_text = "\n".join(
        [f"- {c['category']} (max {c['max_score']} pts): {c['description']}" for c in rubric_criteria]
    )

    prompt = f"""
You are an academic evaluator. Analyze the following presentation slides against the given rubric.

RUBRIC CRITERIA:
{criteria_text}

PRESENTATION CONTENT:
{slide_text}

For each criterion, provide:
1. A score (0 to max_score)
2. A brief explanation (2-3 sentences) justifying the score

Respond in JSON format:
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
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    # TODO: parse JSON from response.text
    return {"raw": response.text}
