.PHONY: install test check benchmark clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

install:
	$(PIP) install -e ".[test]"

test:
	$(PYTHON) -m pytest -q

check:
	$(PYTHON) -m scripts.validate_benchmarks
	$(PYTHON) -m scripts.validate_locales
	$(PYTHON) -m scripts.validate_records --input examples/multilingual.jsonl
	$(PYTHON) -m compileall -q environments evaluation scripts pipelines serving tests

benchmark:
	$(PYTHON) evaluation/run_benchmark.py \
		--benchmark evaluation/benchmarks/ar_tasks_v0.2.json \
		--split development \
		--output benchmark-report.json
	$(PYTHON) -m evaluation.check_regression --report benchmark-report.json

clean:
	rm -rf .pytest_cache .mypy_cache benchmark-report.json
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
