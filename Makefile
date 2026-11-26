# Development commands. Run from the repository root. Each runs inside Docker, so
# only Docker is needed on the developer's machine.

# Containers run as your user, so files they create in backend/ are yours.
export HOST_UID ?= $(shell id -u)
export HOST_GID ?= $(shell id -g)

COMPOSE := docker compose -f deploy/docker-compose.yml
RUN     := $(COMPOSE) run --rm --no-deps web

.DEFAULT_GOAL := help
.PHONY: help env build up down logs ps shell migrate seed makemigrations test lint format \
        makemessages compilemessages schema clean

help: ## List the commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

env: ## Create deploy/.env from deploy/.env.example if it does not exist
	@test -f deploy/.env || (cp deploy/.env.example deploy/.env && echo "Created deploy/.env")

build: env ## Build the backend image
	$(COMPOSE) build

up: env ## Start every service in the background (web on http://localhost:8000)
	$(COMPOSE) up --build --detach --wait web worker beat

down: ## Stop every service (data volumes are kept)
	$(COMPOSE) down

logs: ## Follow the logs of every service
	$(COMPOSE) logs --follow

ps: ## Show the services and their health
	$(COMPOSE) ps --all

shell: env ## Open a Django shell
	$(COMPOSE) run --rm web python manage.py shell

migrate: env ## Compile translations and apply database migrations
	$(COMPOSE) run --rm migrate

seed: env ## Load the default setup data (lists, clinics, chairs, sessions); safe to run again
	$(COMPOSE) run --rm web python manage.py seed_defaults

makemigrations: env ## Create migrations for model changes
	$(COMPOSE) run --rm web python manage.py makemigrations

test: env ## Run pytest (starts db and redis if needed). Extra args: make test ARGS="-k health"
	$(COMPOSE) up --detach --wait db redis
	$(COMPOSE) run --rm web pytest $(ARGS)

lint: env ## Check code style with ruff
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format: env ## Fix code style with ruff
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

makemessages: env ## Collect translatable strings into locale/ar
	$(RUN) python manage.py makemessages --locale ar --ignore ".venv/*" --ignore "*/tests/*"

compilemessages: env ## Compile the Arabic translations
	$(RUN) python manage.py compilemessages --ignore ".venv/*"

schema: env ## Build and validate the OpenAPI schema into backend/schema.yml
	$(RUN) python manage.py spectacular --validate --fail-on-warn --file schema.yml

clean: ## Stop every service and delete its data volumes
	$(COMPOSE) down --volumes
