from __future__ import annotations

import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import get_data_parts, new_data_message
from a2a.types import Role, SendMessageRequest, TaskState


class RemoteAgentError(RuntimeError):
    """Raised when a remote A2A task fails or returns no data artifact."""


async def send_data_task(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Discover an agent, send a JSON data part, and collect its data artifact."""
    async with httpx.AsyncClient(timeout=30) as http:
        card = await A2ACardResolver(http, base_url).get_agent_card()

    client = await create_client(
        card,
        client_config=ClientConfig(
            streaming=True,
            supported_protocol_bindings=["JSONRPC"],
        ),
    )
    message = new_data_message(
        payload,
        media_type="application/json",
        context_id=str(uuid.uuid4()),
        role=Role.ROLE_USER,
    )
    found: dict[str, Any] | None = None
    terminal_state: int | None = None
    try:
        async for event in client.send_message(SendMessageRequest(message=message)):
            if event.HasField("task"):
                terminal_state = event.task.status.state
                for artifact in event.task.artifacts:
                    parts = get_data_parts(artifact.parts)
                    if parts:
                        found = parts[-1]
            elif event.HasField("artifact_update"):
                parts = get_data_parts(event.artifact_update.artifact.parts)
                if parts:
                    found = parts[-1]
            elif event.HasField("status_update"):
                terminal_state = event.status_update.status.state
    finally:
        await client.close()

    failed_states = {
        TaskState.TASK_STATE_FAILED,
        TaskState.TASK_STATE_CANCELED,
        TaskState.TASK_STATE_REJECTED,
    }
    if terminal_state in failed_states:
        raise RemoteAgentError(f"Remote A2A task ended in state {terminal_state}")
    if found is None:
        raise RemoteAgentError("Remote A2A task returned no structured artifact")
    return found
