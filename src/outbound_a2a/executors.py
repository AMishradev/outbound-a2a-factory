from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from a2a.helpers import get_data_parts, new_data_part, new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from pydantic import ValidationError

from outbound_a2a.a2a_client import send_data_task
from outbound_a2a.models import EmailRequest, ResearchBrief
from outbound_a2a.writing import build_email, build_research_brief

logger = logging.getLogger(__name__)


def _payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        raise ValueError("A message is required")
    data_parts = get_data_parts(context.message.parts)
    if not data_parts or not isinstance(data_parts[0], dict):
        raise ValueError("Expected one application/json A2A data part")
    return data_parts[0]


async def _begin(context: RequestContext, queue: EventQueue) -> TaskUpdater:
    if not context.message or not context.task_id or not context.context_id:
        raise ValueError("The A2A request is missing task or context identifiers")
    updater = TaskUpdater(queue, context.task_id, context.context_id)
    await queue.enqueue_event(new_task_from_user_message(context.message))
    await updater.start_work()
    return updater


class ResearchExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = await _begin(context, event_queue)
        try:
            request = EmailRequest.model_validate(_payload(context))
            brief = build_research_brief(request)
            await updater.add_artifact(
                parts=[new_data_part(brief.model_dump(), "application/json")],
                name="research-brief",
                last_chunk=True,
            )
            await updater.complete()
        except (ValueError, ValidationError) as exc:
            await updater.failed(message=updater.new_agent_message([new_data_part(
                {"error": str(exc)}, "application/json"
            )]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()


class DraftExecutor(AgentExecutor):
    def __init__(
        self,
        research_agent_url: str,
        delegate: Callable[
            [str, dict[str, Any]], Awaitable[dict[str, Any]]
        ] = send_data_task,
    ) -> None:
        self.research_agent_url = research_agent_url
        self.delegate = delegate

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = await _begin(context, event_queue)
        try:
            request = EmailRequest.model_validate(_payload(context))
            research_data = await self.delegate(
                self.research_agent_url, request.model_dump()
            )
            brief = ResearchBrief.model_validate(research_data)
            draft = build_email(request, brief)
            await updater.add_artifact(
                parts=[new_data_part(draft.model_dump(), "application/json")],
                name="email-draft",
                last_chunk=True,
            )
            await updater.complete()
        except Exception as exc:  # Task failures must be reported over A2A.
            logger.exception("Draft task failed")
            await updater.failed(message=updater.new_agent_message([new_data_part(
                {"error": str(exc)}, "application/json"
            )]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()
