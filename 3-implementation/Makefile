# Local development uses a venv; delivery uses the container. Both paths are
# first-class, and both are exercised before a change is considered done.

VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
IMAGE   := dataflywheel-selection:1.0.0
INPUT   := data/example_input.jsonl
OUTDIR  := data/example_output

.PHONY: help venv install test run example clean demo verify

help:
	@echo "docker compose up --build   everything, in one command"
	@echo ""
	@echo "make install       create .venv and install the package (editable) with dev deps"
	@echo "make test          run the test suite"
	@echo "make run           run a selection over the committed example input"
	@echo "make example       regenerate the synthetic corpus, then run a selection"
	@echo "make verify        install, test and run — the full local check"
	@echo "make demo          same as docker compose up --build"
	@echo "make clean         remove the venv, caches and generated output"

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)

install: venv
	$(PIP) install -e ".[dev]"

test:
	$(PY) -m pytest

run:
	$(PY) -m dataflywheel_selection --input $(INPUT) --out $(OUTDIR)

example:
	$(PY) data/generate_synthetic.py --count 600 --seed 7 --out $(INPUT)
	$(MAKE) run

verify: install test run
	@echo "ok — installed, tests pass, example selection produced"

demo:
	docker compose up --build

clean:
	rm -rf $(VENV) .pytest_cache *.egg-info src/*.egg-info $(OUTDIR)
	rm -rf output/report.md output/selected.jsonl output/dropped.jsonl output/run_manifest.json output/cold_start
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
