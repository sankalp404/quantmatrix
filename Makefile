.PHONY: up down down-reset ps logs build ladle-up ladle-down ladle-logs ladle-build test-up test test-down

DOCKER ?= docker
PROJECT ?= quantmatrix
PROJECT_TEST ?= quantmatrix_test

ENV_DEV ?= infra/env.dev
ENV_TEST ?= infra/env.test

COMPOSE_DEV = $(DOCKER) compose --project-name $(PROJECT) --env-file $(ENV_DEV) -f infra/compose.dev.yaml
COMPOSE_DEV_UI = $(DOCKER) compose --project-name $(PROJECT) --env-file $(ENV_DEV) -f infra/compose.dev.yaml --profile ui
COMPOSE_TEST = $(DOCKER) compose --project-name $(PROJECT_TEST) --env-file $(ENV_TEST) -f infra/compose.test.yaml

up:
	$(COMPOSE_DEV) up -d --build

down:
	$(COMPOSE_DEV) down

down-reset:
	$(COMPOSE_DEV) down -v

ps:
	$(COMPOSE_DEV) ps

logs:
	$(COMPOSE_DEV) logs --tail=200 backend celery_worker celery_beat frontend

build:
	$(COMPOSE_DEV) build

ladle-up:
	$(COMPOSE_DEV_UI) up -d --build ladle

ladle-down:
	$(COMPOSE_DEV_UI) down

ladle-logs:
	$(COMPOSE_DEV_UI) logs --tail=200 ladle

ladle-build:
	$(COMPOSE_DEV_UI) run --rm ladle npm run ladle:build --silent

test-up:
	$(COMPOSE_TEST) up -d postgres_test redis_test

test:
	$(COMPOSE_TEST) run --rm backend_test

test-down:
	$(COMPOSE_TEST) down -v


