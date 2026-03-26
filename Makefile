.PHONY: up down lint test migrate

up:
	docker compose up --build

down:
	docker compose down

lint:
	docker compose run --rm app ruff check .

test:
	docker compose run --rm app pytest || [ $$? -eq 5 ]

migrate:
	docker compose run --rm app alembic upgrade head
