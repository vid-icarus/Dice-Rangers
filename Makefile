.PHONY: build test lint run clean

build:
	pip install -e ".[dev]"

test:
	pytest tests/

lint:
	ruff check .

run:
	python -m dice_rangers

clean:
	rm -rf build dist *.egg-info dice_rangers.egg-info __pycache__ dice_rangers/__pycache__ tests/__pycache__ .pytest_cache .ruff_cache
