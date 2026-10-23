.PHONY: install test lint typecheck imports check up

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	ruff check .

typecheck:
	mypy src

imports:
	lint-imports

check: lint typecheck imports test

up:
	@echo "The application services are not configured yet. This target will be enabled with the first runnable backend/frontend slice."
