import time
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)


def analyze_video(video_path: str, rubric_criteria: list) -> dict:
    """Upload video to Gemini Files API and analyze against rubric."""
    criteria_text = "\n".join(
        [f"- {c['category']} (max {c['max_score']} pts): {c['description']}" for c in rubric_criteria]
    )

    print(f"Uploading video to Gemini Files API: {video_path}")
    video_file = genai.upload_file(path=video_path)

    # Wait for Gemini to process the video
    while video_file.state.name == "PROCESSING":
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError(f"Gemini video processing failed: {video_file.state.name}")

    prompt = f"""
You are an academic evaluator watching a student project demo video.
Analyze the video against the following rubric criteria.

RUBRIC CRITERIA:
{criteria_text}

For each criterion, provide:
1. A score (0 to max_score)
2. A brief explanation (2-3 sentences) based on what you observed in the video

Respond in JSON format:
{{
  "criteria_scores": [
    {{
      "category": "<criterion name>",
      "score": <number>,
      "comment": "<explanation>"
    }}
  ],
  "video_summary": "<2-3 sentence summary of what was demonstrated in the video>"
}}
"""
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content([video_file, prompt])

    # Clean up uploaded file
    genai.delete_file(video_file.name)

    # TODO: parse JSON from response.text
    return {"raw": response.text}
