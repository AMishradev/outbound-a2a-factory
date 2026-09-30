from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path

import uvicorn

from outbound_a2a.a2a_client import send_data_task
from outbound_a2a.models import EmailRequest
from outbound_a2a.server import create_app


def example_request() -> EmailRequest:
    return EmailRequest(
        sender_name="Maya",
        sender_company="Northstar",
        recipient_name="Jordan",
        recipient_role="VP of Sales",
        recipient_company="Acme",
        offering="an outbound workflow platform",
        pain_point="sales reps spend too much time drafting follow-ups",
        proof_point="similar teams cut drafting time by 40%",
        call_to_action="Would a 15-minute conversation next week be useful?",
    )


async def _demo(url: str, input_file: str | None) -> None:
    payload = (
        json.loads(Path(input_file).read_text(encoding="utf-8"))
        if input_file
        else example_request().model_dump()
    )
    result = await send_data_task(url, payload)
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Outbound email factory over A2A")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run one A2A agent")
    serve.add_argument("kind", choices=["research", "draft"])

    demo = subparsers.add_parser("demo", help="Send one task to the Draft Agent")
    demo.add_argument("--url", default="http://localhost:8002")
    demo.add_argument("--input", help="Path to an EmailRequest JSON file")

    args = parser.parse_args()
    if args.command == "demo":
        asyncio.run(_demo(args.url, args.input))
        return

    port = int(os.getenv("PORT", "8001" if args.kind == "research" else "8002"))
    public_url = os.getenv("AGENT_PUBLIC_URL", f"http://localhost:{port}")
    app = create_app(
        args.kind,
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://a2a:a2a@localhost:5432/outbound_factory",
        ),
        public_url=public_url,
        research_agent_url=os.getenv(
            "RESEARCH_AGENT_URL", "http://localhost:8001"
        ),
    )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
