from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from handfont_capture.models import SessionOptions
from handfont_capture.session import process_capture_session
from handfont_capture.synthetic import generate_benchmark_session


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=20260728)
    args = parser.parse_args()
    generated = generate_benchmark_session(args.output, seed=args.seed, dpi=150)
    complete_output = args.output / "processed-complete"
    complete = process_capture_session(
        [generated["photos"]],
        complete_output,
        SessionOptions(dpi=150, vectorize=True, vectorize_limit=64, min_page_confidence=0.25),
        manual_corners_path=generated["manual_corners"],
    )
    missing_photos = args.output / "photos-missing-page-05"
    missing_photos.mkdir(parents=True, exist_ok=True)
    for path in generated["photos"].glob("*.jpg"):
        truth = next((item for item in generated["ground_truth"]["records"] if item["file"] == path.name), None)
        if truth and truth["page"] == 5:
            continue
        target = missing_photos / path.name
        target.write_bytes(path.read_bytes())
    missing_output = args.output / "processed-missing-page-05"
    missing = process_capture_session(
        [missing_photos],
        missing_output,
        SessionOptions(dpi=150, vectorize=False, min_page_confidence=0.25),
        manual_corners_path=generated["manual_corners"],
    )
    payload = {
        "schema_version": "1.8.0",
        "complete_session": {
            "complete": complete["complete"],
            "selected_pages": complete["selected_pages"],
            "manual_pages": complete["manual_pages"],
            "duplicate_pages": complete["duplicate_pages"],
            "failed_inputs": complete["failed_inputs"],
            "position_coverage": complete["position_coverage"],
            "vectorization": {
                "processed": complete["vectorization"]["processed"],
                "failed_or_skipped": complete["vectorization"]["failed_or_skipped"],
            },
        },
        "missing_page_session": {
            "complete": missing["complete"],
            "selected_pages": missing["selected_pages"],
            "missing_pages": missing["missing_pages"],
        },
    }
    (args.output / "benchmark-summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
