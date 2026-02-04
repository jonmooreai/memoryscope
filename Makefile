.PHONY: setup up down migrate test clean

setup:
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "Created .env from env.example"; \
	fi

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest -q

test-verbose:
	docker compose exec api pytest -v

shell:
	docker compose exec api /bin/bash

logs:
	docker compose logs -f api

clean:
	docker compose down -v
	rm -f .env

# Deployment
deploy:
	./deploy-all.sh

deploy-website:
	./deploy-all.sh --website-only

deploy-api:
	./deploy-all.sh --api-only

# Convenience target that does everything
all: setup up migrate test

