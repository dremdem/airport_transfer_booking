.PHONY: help build up down lint format check test migrate seed-demo db-revision db-reset db-connect

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Rebuild all Docker images (app + frontend — run after dependency or Dockerfile changes)
	docker compose build

up: ## Start all services in background: db, app, frontend (http://localhost:3000)
	docker compose up -d

down: ## Stop and remove containers
	docker compose down

lint: ## Run ruff linter
	docker compose run --rm --no-deps app ruff check .

format: ## Run ruff formatter
	docker compose run --rm --no-deps app ruff format .

check: lint ## Run all code quality checks

test: ## Run the full test suite
	docker compose run --rm app pytest || [ $$? -eq 5 ]

migrate: ## Apply pending migrations
	docker compose run --rm app alembic upgrade head

seed-demo: ## Seed demo bookings into the live database (appends — safe to run multiple times)
	docker compose run --rm app python scripts/seed_demo_data.py

db-revision: ## Create a new migration (usage: make db-revision MSG="describe change")
	docker compose run --rm app alembic revision --autogenerate -m "$(MSG)"

db-reset: ## Downgrade all migrations (wipe schema)
	docker compose run --rm app alembic downgrade base

db-connect: ## Open an interactive MySQL shell in the running db container
	docker compose exec db mysql -uroot -proot transfer_bookings
