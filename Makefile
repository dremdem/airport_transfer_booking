.PHONY: help up down lint format check test migrate db-revision db-reset

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Build and start all services in background
	docker compose up --build -d

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

db-revision: ## Create a new migration (usage: make db-revision MSG="describe change")
	docker compose run --rm app alembic revision --autogenerate -m "$(MSG)"

db-reset: ## Downgrade all migrations (wipe schema)
	docker compose run --rm app alembic downgrade base
