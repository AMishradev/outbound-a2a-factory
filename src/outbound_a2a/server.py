from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import DatabaseTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from outbound_a2a.executors import DraftExecutor, ResearchExecutor

AgentKind = Literal["research", "draft"]


def _card(kind: AgentKind, public_url: str) -> AgentCard:
    if kind == "research":
        name = "Outbound Research Agent"
        description = "Turns supplied prospect facts into a grounded messaging brief."
        skill = AgentSkill(
            id="build_research_brief",
            name="Build research brief",
            description="Structures supplied prospect context without inventing facts.",
            tags=["outbound", "research", "email"],
            examples=["Create a messaging brief for this prospect."],
            input_modes=["application/json"],
            output_modes=["application/json"],
        )
    else:
        name = "Outbound Draft Agent"
        description = "Delegates research over A2A and drafts a professional email."
        skill = AgentSkill(
            id="draft_outbound_email",
            name="Draft outbound email",
            description=(
                "Creates a concise email from structured sender and prospect data."
            ),
            tags=["outbound", "email", "writing"],
            examples=["Draft an email to a VP of Sales."],
            input_modes=["application/json"],
            output_modes=["application/json"],
        )
    return AgentCard(
        name=name,
        description=description,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[skill],
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                protocol_version="1.0",
                url=f"{public_url.rstrip('/')}/a2a/jsonrpc",
            )
        ],
    )


def create_app(
    kind: AgentKind,
    database_url: str,
    public_url: str,
    research_agent_url: str = "http://research-agent:8001",
) -> FastAPI:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    task_store = DatabaseTaskStore(
        engine,
        table_name=f"{kind}er_tasks" if kind == "draft" else "researcher_tasks",
    )
    card = _card(kind, public_url)
    executor = (
        ResearchExecutor()
        if kind == "research"
        else DraftExecutor(research_agent_url=research_agent_url)
    )
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=card,
        validate_input_modes=True,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await task_store.initialize()
        yield
        await engine.dispose()

    app = FastAPI(title=card.name, version="0.1.0", lifespan=lifespan)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(card),
        jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url="/a2a/jsonrpc"),
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "agent": kind}

    return app
