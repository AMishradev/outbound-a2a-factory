.PHONY: install lint test up down demo logs db

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check .

test:
	pytest -q

up:
	docker compose up --build -d

down:
	docker compose down

demo:
	docker compose exec draft-agent outbound-a2a demo --url http://draft-agent:8002

logs:
	docker compose logs -f research-agent draft-agent

db:
	docker compose exec postgres psql -U a2a -d outbound_factory -c "SELECT id, status->>'state' AS state, json_array_length(history) AS messages, json_array_length(artifacts) AS artifacts FROM researcher_tasks UNION ALL SELECT id, status->>'state', json_array_length(history), json_array_length(artifacts) FROM drafter_tasks;"
