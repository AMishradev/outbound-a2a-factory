# Outbound A2A Factory

A deliberately small outbound-email system for learning the **Agent2Agent
(A2A) protocol**. (The protocol is A2A, not ADA.) Two independently served
agents discover and call each other using A2A 1.0 over JSON-RPC; PostgreSQL
persists the protocol tasks, message history, statuses, and artifacts.

This is a protocol lab, not a production sales automation product. The writing
logic is deterministic on purpose, so the A2A traffic and persisted state stay
easy to inspect before an LLM or CRM is added.

## What happens

```text
CLI / caller
    |
    | A2A: SendMessage(EmailRequest data part)
    v
Draft Agent :8002
    |
    | GET /.well-known/agent-card.json
    | A2A JSON-RPC: SendMessage(EmailRequest data part)
    v
Research Agent :8001
    |
    | A2A artifact: ResearchBrief
    v
Draft Agent
    |
    | A2A artifact: EmailDraft
    v
CLI / caller
```

There is no private Python call between the agents. The Draft Agent knows only
the Research Agent's base URL, discovers its Agent Card, negotiates JSON-RPC,
sends a protocol message, and consumes the returned protocol artifact.

## Run it

Requirements: Docker with Compose.

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec draft-agent outbound-a2a demo --url http://draft-agent:8002
```

Or use the shortcuts:

```bash
make up
make demo
make db
make logs
```

The Agent Cards are available from the host at:

- Research: <http://localhost:8001/.well-known/agent-card.json>
- Draft: <http://localhost:8002/.well-known/agent-card.json>

Health endpoints are `/health`; protocol traffic goes to `/a2a/jsonrpc`.

To send custom input, create a JSON file matching `EmailRequest` in
`src/outbound_a2a/models.py`, then run:

```bash
docker compose exec draft-agent outbound-a2a demo \
  --url http://draft-agent:8002 --input /path/inside/container/request.json
```

The Compose Agent Cards intentionally advertise Docker-network addresses so
the independently containerized agents can reach each other. To run both
agents directly on the host instead, install the project and start them in
separate terminals with host-facing card URLs:

```bash
python -m pip install -e '.[dev]'

AGENT_PUBLIC_URL=http://localhost:8001 PORT=8001 \
  outbound-a2a serve research

AGENT_PUBLIC_URL=http://localhost:8002 PORT=8002 \
  RESEARCH_AGENT_URL=http://localhost:8001 outbound-a2a serve draft

outbound-a2a demo --url http://localhost:8002 --input request.json
```

## Inspect Postgres

The official A2A SDK `DatabaseTaskStore` owns two tables:

- `researcher_tasks`: the inter-agent delegation, request history, brief, and status
- `drafter_tasks`: the caller request, final email artifact, and status

Inspect a compact task list with `make db`, or open psql:

```bash
docker compose exec postgres psql -U a2a -d outbound_factory
```

Useful queries:

```sql
SELECT id, context_id, status, history, artifacts FROM drafter_tasks;
SELECT id, context_id, status, history, artifacts FROM researcher_tasks;
```

Postgres is persistence, not a transport. The agents communicate over A2A;
they do not poll database rows as a homemade queue.

## A2A concepts demonstrated

- Agent discovery through the standard well-known Agent Card
- Skills, capabilities, input modes, output modes, and supported interfaces
- Structured JSON data parts rather than prompt-shaped strings
- Task lifecycle: submitted → working → completed/failed
- Streaming status and artifact update events
- Agent-to-agent delegation using the same client surface as any remote caller
- Durable A2A task storage through the SDK's Postgres implementation
- Independent agent processes and network addresses

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
```

The repository pins `a2a-sdk==1.2.0` because the SDK's 1.x API differs
substantially from older A2A examples. The public protocol surface used here is
A2A 1.0 JSON-RPC.

## Scope and next steps

The Research Agent currently restructures facts supplied by the caller; it
does not browse the web. That avoids fabricated personalization while the
project is focused on learning A2A. Natural extensions are:

1. Put an LLM behind each executor while keeping their A2A contracts stable.
2. Add authentication and signed Agent Cards before exposing either agent.
3. Add a human approval task before sending any email.
4. Add a third delivery agent only after the two-agent flow is understood.

Treat every remote Agent Card, message, and artifact as untrusted input in a
real deployment. This lab validates its structured payloads, but it is not an
internet-facing security boundary.

## References

- [A2A protocol documentation](https://a2a-protocol.org/)
- [Official Python SDK](https://github.com/a2aproject/a2a-python)
- [Official samples](https://github.com/a2aproject/a2a-samples)
