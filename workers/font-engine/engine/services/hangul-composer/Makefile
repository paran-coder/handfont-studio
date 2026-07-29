PYTHON ?= python
PROJECT := $(abspath ../..)
HANGUL := $(PROJECT)/services/hangul-engine/examples/hangul-source-v1.6.0
OUTPUT := $(CURDIR)/examples/composition-benchmark-v1.7.0

.PHONY: test benchmark

test:
	PYTHONPATH=$(CURDIR):$(PROJECT)/services/hangul-engine $(PYTHON) -m pytest

benchmark:
	PYTHONPATH=$(CURDIR):$(PROJECT)/services/hangul-engine $(PYTHON) -m handfont_hangul_composer \
		--position-map $(HANGUL)/hangul-position-map.json \
		--source-masks $(HANGUL)/masks \
		--output $(OUTPUT) \
		--vectorizer-root $(PROJECT)/services/glyph-vectorizer \
		--font-builder-root $(PROJECT)/services/font-builder \
		--limit 500
