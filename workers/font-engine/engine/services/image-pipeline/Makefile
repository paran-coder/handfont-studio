.PHONY: test benchmark demo

test:
	PYTHONPATH=. pytest

benchmark:
	PYTHONPATH=. python scripts/benchmark.py --output examples/benchmark-v1.3.0 --dpi 150 --seed 20260728

demo:
	PYTHONPATH=. python -m handfont_pipeline.cli process --input ../../handfont-writing-template-v1.3.0.pdf --pdf-page 2 --template-page 1 --output examples/pristine-page-01 --dpi 150
