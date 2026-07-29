PYTHON ?= python
PROJECT_ROOT := ../..
SOURCE := examples/hangul-source-v1.6.0
FONT_OUTPUT := examples/hangul-font-v1.6.0

test:
	PYTHONPATH=. $(PYTHON) -m pytest

generate:
	PYTHONPATH=. $(PYTHON) -m handfont_hangul.cli --output $(SOURCE) --charset $(PROJECT_ROOT)/character-set-v1.3.0.csv --vectorizer-root ../glyph-vectorizer

validate:
	PYTHONPATH=.:../font-builder $(PYTHON) scripts/validate_poc.py --source $(SOURCE) --font-output $(FONT_OUTPUT) --output validation-summary-v1.6.0.json
