.PHONY: test build-poc

test:
	PYTHONPATH=. pytest

build-poc:
	PYTHONPATH=. python scripts/generate_poc_dataset.py --output examples/poc-source-v1.5.0
	PYTHONPATH=. python -m handfont_fontbuilder.cli build --manifest examples/poc-source-v1.5.0/glyph-manifest.json --output examples/poc-font-v1.5.0
