from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


GEMINI_25_FLASH_INPUT_PER_MILLION = 0.30
GEMINI_25_FLASH_OUTPUT_PER_MILLION = 2.50
GEMINI_25_FLASH_CACHED_INPUT_PER_MILLION = 0.03


@dataclass
class UsageTotals:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_prompt_tokens: int = 0
    total_tokens: int = 0
    successful_requests: int = 0
    estimated_cost_usd: float = 0.0
    entries: list[dict[str, Any]] = field(default_factory=list)


_USAGE_TOTALS: ContextVar[UsageTotals | None] = ContextVar("usage_totals", default=None)


@contextmanager
def usage_tracking_context():
    totals = UsageTotals()
    token: Token[UsageTotals | None] = _USAGE_TOTALS.set(totals)
    try:
        yield totals
    finally:
        _USAGE_TOTALS.reset(token)


def summarize_usage(label: str, model: str, usage_metrics: Any) -> dict[str, Any] | None:
    if usage_metrics is None:
        return None

    prompt_tokens = int(getattr(usage_metrics, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage_metrics, "completion_tokens", 0) or 0)
    cached_prompt_tokens = int(getattr(usage_metrics, "cached_prompt_tokens", 0) or 0)
    total_tokens = int(getattr(usage_metrics, "total_tokens", prompt_tokens + completion_tokens) or 0)
    successful_requests = int(getattr(usage_metrics, "successful_requests", 0) or 0)
    estimated_cost_usd = estimate_cost_usd(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cached_prompt_tokens=cached_prompt_tokens,
    )

    summary = {
        "label": label,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cached_prompt_tokens": cached_prompt_tokens,
        "total_tokens": total_tokens,
        "successful_requests": successful_requests,
        "estimated_cost_usd": estimated_cost_usd,
    }
    _record_summary(summary)
    return summary


def format_usage_summary(summary: dict[str, Any]) -> str:
    return (
        f"{summary['label']} usage metrics: "
        f"total_tokens={summary['total_tokens']} "
        f"prompt_tokens={summary['prompt_tokens']} "
        f"cached_prompt_tokens={summary['cached_prompt_tokens']} "
        f"completion_tokens={summary['completion_tokens']} "
        f"successful_requests={summary['successful_requests']} "
        f"estimated_cost_usd=${summary['estimated_cost_usd']:.6f}"
    )


def format_usage_totals(label: str, totals: UsageTotals) -> str:
    return (
        f"{label}: "
        f"total_tokens={totals.total_tokens} "
        f"prompt_tokens={totals.prompt_tokens} "
        f"cached_prompt_tokens={totals.cached_prompt_tokens} "
        f"completion_tokens={totals.completion_tokens} "
        f"successful_requests={totals.successful_requests} "
        f"estimated_cost_usd=${totals.estimated_cost_usd:.6f}"
    )


def estimate_cost_usd(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_prompt_tokens: int = 0,
) -> float:
    normalized_model = model.lower()
    if "gemini-2.5-flash" in normalized_model:
        non_cached_prompt_tokens = max(prompt_tokens - cached_prompt_tokens, 0)
        input_cost = (non_cached_prompt_tokens / 1_000_000) * GEMINI_25_FLASH_INPUT_PER_MILLION
        cached_input_cost = (cached_prompt_tokens / 1_000_000) * GEMINI_25_FLASH_CACHED_INPUT_PER_MILLION
        output_cost = (completion_tokens / 1_000_000) * GEMINI_25_FLASH_OUTPUT_PER_MILLION
        return round(input_cost + cached_input_cost + output_cost, 6)
    return 0.0


def _record_summary(summary: dict[str, Any]) -> None:
    totals = _USAGE_TOTALS.get()
    if totals is None:
        return
    totals.prompt_tokens += int(summary["prompt_tokens"])
    totals.completion_tokens += int(summary["completion_tokens"])
    totals.cached_prompt_tokens += int(summary["cached_prompt_tokens"])
    totals.total_tokens += int(summary["total_tokens"])
    totals.successful_requests += int(summary["successful_requests"])
    totals.estimated_cost_usd = round(totals.estimated_cost_usd + float(summary["estimated_cost_usd"]), 6)
    totals.entries.append(summary)
