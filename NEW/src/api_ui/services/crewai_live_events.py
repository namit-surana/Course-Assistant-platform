from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any

from crewai.events.base_event_listener import BaseEventListener
from crewai.events.event_bus import CrewAIEventsBus
from crewai.events.types.agent_events import (
    AgentExecutionCompletedEvent,
    AgentExecutionStartedEvent,
)
from crewai.events.types.llm_events import LLMCallStartedEvent
from crewai.events.types.reasoning_events import (
    AgentReasoningCompletedEvent,
    AgentReasoningStartedEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)

from src.api_ui.services.run_store import RunProgressReporter


@dataclass(slots=True)
class CrewRunBinding:
    reporter: RunProgressReporter
    phase_id: str
    default_subtask_id: str | None = None
    task_name_map: dict[str, str] = field(default_factory=dict)


_RUN_BINDING: ContextVar[CrewRunBinding | None] = ContextVar("crewai_run_binding", default=None)


@contextmanager
def bind_crewai_run_context(
    reporter: RunProgressReporter,
    *,
    phase_id: str,
    default_subtask_id: str | None = None,
    task_name_map: dict[str, str] | None = None,
):
    token: Token[CrewRunBinding | None] = _RUN_BINDING.set(
        CrewRunBinding(
            reporter=reporter,
            phase_id=phase_id,
            default_subtask_id=default_subtask_id,
            task_name_map=task_name_map or {},
        )
    )
    try:
        yield
    finally:
        _RUN_BINDING.reset(token)


class CrewAIRunEventBridge(BaseEventListener):
    """Bridges CrewAI runtime events into the live run store."""

    def setup_listeners(self, crewai_event_bus: CrewAIEventsBus):
        @crewai_event_bus.on(AgentExecutionStartedEvent)
        def on_agent_started(_: Any, event: AgentExecutionStartedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, event.task, None)
            if subtask_id is None:
                return
            message = f"{event.agent.role} is analyzing this step"
            binding.reporter.patch_subtask(
                binding.phase_id,
                subtask_id,
                detail=message,
                badges=[event.agent.role],
            )
            binding.reporter.event(
                "agent-started",
                message,
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=[event.agent.role],
            )

        @crewai_event_bus.on(AgentExecutionCompletedEvent)
        def on_agent_completed(_: Any, event: AgentExecutionCompletedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, event.task, None)
            if subtask_id is None:
                return
            binding.reporter.event(
                "agent-completed",
                f"{event.agent.role} finished its pass",
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=[event.agent.role],
            )

        @crewai_event_bus.on(AgentReasoningStartedEvent)
        def on_reasoning_started(_: Any, event: AgentReasoningStartedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, None, event.task_name)
            if subtask_id is None:
                return
            binding.reporter.event(
                "reasoning-started",
                f"{event.agent_role} is reasoning about the next step",
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=[event.agent_role],
            )

        @crewai_event_bus.on(AgentReasoningCompletedEvent)
        def on_reasoning_completed(_: Any, event: AgentReasoningCompletedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, None, event.task_name)
            if subtask_id is None:
                return
            plan_text = " ".join(event.plan.split()) if event.plan else "Reasoning completed"
            message = f"{event.agent_role} decided the next move"
            binding.reporter.patch_subtask(
                binding.phase_id,
                subtask_id,
                detail=plan_text[:220],
                badges=[event.agent_role],
            )
            binding.reporter.event(
                "reasoning-completed",
                message,
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=[event.agent_role],
            )

        @crewai_event_bus.on(LLMCallStartedEvent)
        def on_llm_started(_: Any, event: LLMCallStartedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, getattr(event, "from_task", None), event.task_name)
            if subtask_id is None:
                return
            badges = [item for item in [event.agent_role, event.model] if item]
            binding.reporter.event(
                "llm-started",
                f"{event.agent_role or 'Agent'} is generating a response",
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=badges,
            )

        @crewai_event_bus.on(ToolUsageStartedEvent)
        def on_tool_started(_: Any, event: ToolUsageStartedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, getattr(event, "from_task", None), event.task_name)
            if subtask_id is None:
                return
            message = _format_tool_message(event.tool_name, event.tool_args, started=True)
            badges = [event.tool_name]
            binding.reporter.patch_subtask(
                binding.phase_id,
                subtask_id,
                detail=message,
                badges=badges,
            )
            binding.reporter.event(
                "tool-started",
                message,
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=badges,
            )

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def on_tool_finished(_: Any, event: ToolUsageFinishedEvent) -> None:
            binding = _RUN_BINDING.get()
            if binding is None:
                return
            subtask_id = _resolve_subtask_id(binding, getattr(event, "from_task", None), event.task_name)
            if subtask_id is None:
                return
            output_preview = str(event.output).strip().replace("\n", " ")
            if len(output_preview) > 140:
                output_preview = output_preview[:137] + "..."
            message = _format_tool_message(event.tool_name, event.tool_args, started=False)
            detail = output_preview or message
            binding.reporter.patch_subtask(
                binding.phase_id,
                subtask_id,
                detail=detail,
                badges=[event.tool_name],
            )
            binding.reporter.event(
                "tool-finished",
                message,
                phase_id=binding.phase_id,
                subtask_id=subtask_id,
                badges=[event.tool_name],
            )


def _resolve_subtask_id(
    binding: CrewRunBinding,
    task: Any | None,
    task_name: str | None,
) -> str | None:
    raw_name = task_name
    if raw_name is None and task is not None:
        raw_name = getattr(task, "name", None)
    if raw_name is not None and raw_name in binding.task_name_map:
        return binding.task_name_map[raw_name]
    return binding.default_subtask_id
def _format_tool_message(tool_name: str, tool_args: Any, *, started: bool) -> str:
    action = "Using" if started else "Finished"
    path = None
    start_line = None
    max_lines = None
    if isinstance(tool_args, dict):
        path = tool_args.get("path")
        start_line = tool_args.get("start_line")
        max_lines = tool_args.get("max_lines")
    line_range = None
    if isinstance(start_line, int) and isinstance(max_lines, int):
        line_range = f" lines {start_line}-{start_line + max_lines - 1}"
    if path:
        suffix = line_range or ""
        return f"{action} {tool_name} on {path}{suffix}"
    return f"{action} {tool_name}"


RUN_EVENT_BRIDGE = CrewAIRunEventBridge()
