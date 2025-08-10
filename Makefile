.PHONY: check lint type test

check:
	scripts/check.sh

lint:
	python -m ruff check .

type:
	python -m mypy src

test:
	python -m pytest -q
