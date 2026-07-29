.PHONY: up build down logs migrate migrations seed superuser test backend-test frontend-test check smoke shell

COMPOSE := docker compose

up:
	$(COMPOSE) up --build -d

build:
	$(COMPOSE) build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=150

migrate:
	$(COMPOSE) exec backend python manage.py migrate

migrations:
	$(COMPOSE) --profile test run --rm --build \
		--volume ./backend:/app/backend backend-test \
		python manage.py makemigrations

seed:
	$(COMPOSE) exec backend python manage.py seed_demo

superuser:
	$(COMPOSE) exec backend python manage.py createsuperuser

test: backend-test frontend-test

backend-test:
	$(COMPOSE) --profile test run --rm --build backend-test

frontend-test:
	$(COMPOSE) --profile test run --rm frontend-test

check:
	$(COMPOSE) exec backend python manage.py check
	$(COMPOSE) exec backend python manage.py makemigrations --check --dry-run

smoke:
	sh ./scripts/smoke-test.sh

shell:
	$(COMPOSE) exec backend python manage.py shell
