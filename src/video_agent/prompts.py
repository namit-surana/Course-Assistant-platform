from .models import RubricCriterion, VideoAnalysisMode


def build_video_analysis_prompt(
    rubric_criteria: list[RubricCriterion],
    analysis_mode: VideoAnalysisMode,
) -> str:
    criteria_text = "\n".join(
        [
            (
                f"{index}. Category: {criterion.category}\n"
                f"   Max score: {criterion.max_score}\n"
                f"   Description: {criterion.description}"
            )
            for index, criterion in enumerate(rubric_criteria, start=1)
        ]
    )

    mode_instruction = (
        "You are evaluating the full uploaded video, including spoken audio, visual demonstrations, "
        "screen recordings, slides shown in the video, UI walkthroughs, code demos, timing, clarity, "
        "and completeness."
        if analysis_mode == VideoAnalysisMode.FULL_VIDEO
        else
        "You are evaluating only the transcript/audio-derived content. You must not claim to have seen "
        "visual demonstrations, UI screens, code walkthroughs, or slides unless they are explicitly described "
        "in the transcript."
    )

    return f"""
You are an expert academic project evaluator.

Evaluation mode:
{analysis_mode.value}

Important context:
{mode_instruction}

Rubric criteria:
{criteria_text}

Evaluation rules:
- Evaluate every rubric criterion independently.
- Score each criterion from 0 to its max_score.
- Do not invent evidence.
- If evidence is missing or unclear, give a lower score and clearly say what is missing.
- Prefer specific evidence from the video/transcript over generic praise.
- Penalize unclear demos, missing explanations, incomplete walkthroughs, or unsupported claims.
- Keep comments concise but useful for students.
- The score must never exceed max_score.
- The score must never be negative.
- Return only valid JSON.
- Do not include markdown.
- Do not include explanations outside JSON.

Return exactly this JSON structure:
{{
  "criteria_scores": [
    {{
      "category": "same category name from rubric",
      "score": 0,
      "max_score": 0,
      "comment": "brief scoring justification",
      "evidence": "specific evidence observed or missing"
    }}
  ],
  "video_summary": "2-3 sentence overall summary of the project demo/video.",
  "warnings": []
}}
""".strip()