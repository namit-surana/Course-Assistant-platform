from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, including fenced blocks."""
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


def generative_model_name(crew_or_litellm_model: str) -> str:
    """Strip LiteLLM-style `gemini/` prefix for Gemini SDK calls."""
    if "/" in crew_or_litellm_model:
        return crew_or_litellm_model.split("/", 1)[-1]
    return crew_or_litellm_model
