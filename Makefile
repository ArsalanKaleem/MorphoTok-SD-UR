# MorphoTok-SD-UR task runner. Every target defaults to the SYNTHETIC dataset.
# Use DATA=sindhi or DATA=urdu once real resources are configured.
# On Windows without `make`, use: python scripts/make_targets.py <target> [--data X]

DATA   ?= synthetic
CONFIG ?= configs/run/default.yaml
PYBASE ?= python3.11

ifeq ($(OS),Windows_NT)
  PY := .venv/Scripts/python
else
  PY := .venv/bin/python
endif

RUN := $(PY) -X utf8
ARGS := --config $(CONFIG) --data $(DATA)

.PHONY: setup lint format test gate0 gate1 gate2 tokenizer intrinsic ablations lmproxy \
        real-data review-sheets review-ingest fixture prereg-status prereg-freeze clean

setup:
	$(PYBASE) -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.lock
	$(PY) -m pip install --no-deps -e .
	-$(PY) -m pre_commit install

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

test:
	$(RUN) -m pytest

# Gate 0: baselines x normalization policies at matched vocabulary sizes (prints a table)
gate0:
	$(RUN) scripts/01_baseline_fertility.py $(ARGS)

# Gate 1: ZWNJ context report + annotation sheet
gate1:
	$(RUN) scripts/00_zwnj_audit.py $(ARGS)

# Gate 2: analyzer coverage; states explicitly when no real analyzer is configured
gate2:
	$(RUN) scripts/02_analyzer_coverage.py $(ARGS)

tokenizer:
	$(RUN) scripts/03_train_tokenizers.py $(ARGS)

intrinsic:
	$(RUN) scripts/04_intrinsic_eval.py $(ARGS)

ablations:
	$(RUN) scripts/05_ablation_grid.py $(ARGS)

# Gate 5 proxy: token-bigram bits per character (NOT a neural LM)
lmproxy:
	$(RUN) scripts/06_lm_proxy.py $(ARGS)

# Rebuild real-data pilots, silver supervision and the Zia gold from data/raw/
# (download first: see data/raw/SOURCE.md). Needs the [data] extra (pyarrow).
real-data:
	for l in sd ur; do $(RUN) scripts/prepare_wikipedia.py $$l --n-lines 5000; $(RUN) scripts/build_silver.py $$l; done
	$(RUN) scripts/build_zia_gold.py

# Native-speaker review (audit/REVIEWING.md): create sheets once, then check/import answers
review-sheets:
	$(RUN) scripts/make_review_sheets.py

review-ingest:
	$(RUN) scripts/ingest_review.py

fixture:
	$(RUN) -m morphtok.data.synthetic

prereg-status:
	$(RUN) scripts/prereg_freeze.py status

prereg-freeze:
	$(RUN) scripts/prereg_freeze.py freeze

clean:
	rm -rf runs .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
