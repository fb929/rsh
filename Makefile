.PHONY: help dev test build install clean

VENV  := .venv
PY    := $(VENV)/bin/python
STAMP := $(VENV)/.install-stamp

help:   ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n", $$1, $$2}'

# (re)create the venv and install the package (editable) with dev + ovh extras;
# re-runs automatically whenever pyproject.toml changes
$(STAMP): pyproject.toml
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install --editable '.[dev,ovh]'
	@touch $(STAMP)

dev: $(STAMP)   ## create .venv and install rsh with dev + ovh extras (editable)
	@echo 'ready - run "source $(VENV)/bin/activate" to put sr/sExec/pExec on PATH'

test: $(STAMP)  ## run the test suite in .venv
	$(PY) -m pytest

build: $(STAMP) ## build sdist + wheel into dist/
	$(PY) -m build

install:        ## install into the ACTIVE environment (for deploy, not the .venv)
	pip install .

clean:          ## remove .venv, build artifacts and caches
	rm -rf $(VENV) build/ dist/ *.egg-info rsh.egg-info .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
