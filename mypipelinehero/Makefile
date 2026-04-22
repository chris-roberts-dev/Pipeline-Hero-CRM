# MyPipelineHero — common developer commands.
#
# Every target runs against the compose stack unless noted otherwise.
# `make help` lists everything.

.PHONY: help up down build rebuild logs shell dbshell migrate makemigrations \
        createsuperuser test lint format check clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up:  ## Start the full stack in the background
	docker compose up -d

down:  ## Stop the stack (keeps volumes)
	docker compose down

build:  ## Build all images
	docker compose build

rebuild:  ## Build all images without cache
	docker compose build --no-cache

logs:  ## Tail logs for all services
	docker compose logs -f

shell:  ## Django shell (shell_plus if django-extensions installed)
	docker compose exec django python manage.py shell_plus 2>/dev/null || \
	docker compose exec django python manage.py shell

dbshell:  ## psql into the postgres container
	docker compose exec postgres psql -U mph -d mph

migrate:  ## Apply migrations
	docker compose exec django python manage.py migrate

makemigrations:  ## Generate migrations for changed models
	docker compose exec django python manage.py makemigrations

createsuperuser:  ## Create a Django superuser
	docker compose exec django python manage.py createsuperuser

test:  ## Run pytest inside the django container
	docker compose exec django pytest

lint:  ## Run ruff linter
	docker compose exec django ruff check .

format:  ## Run ruff formatter
	docker compose exec django ruff format .

check:  ## Run Django's deploy-check
	docker compose exec django python manage.py check --deploy

clean:  ## Remove stopped containers, volumes, and dangling images (destructive)
	docker compose down -v
	docker image prune -f
