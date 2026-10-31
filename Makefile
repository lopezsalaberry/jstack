.PHONY: test lint
test: lint
	python3 -m pytest -q tests
lint:
	shellcheck install.sh
	python3 tools/lint.py
