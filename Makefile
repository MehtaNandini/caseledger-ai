.PHONY: run test lint docker-up
run:
	uvicorn app.main:app --reload

test:
	pytest -q

lint:
	ruff check app tests

docker-up:
	docker compose up --build
