from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(prog="handfont-hangul-composer")
    parser.add_argument("--position-map", type=Path, required=True)
    parser.add_argument("--source-masks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vectorizer-root", type=Path, required=True)
    parser.add_argument("--font-builder-root", type=Path)
    parser.add_argument("--reference-font", type=Path)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    summary = run_benchmark(
        position_map=args.position_map,
        source_masks=args.source_masks,
        output_dir=args.output,
        vectorizer_root=args.vectorizer_root,
        font_builder_root=args.font_builder_root,
        reference_font=args.reference_font,
        limit=args.limit,
    )
    print(json.dumps({
        "generated": summary["benchmark_generated"],
        "failures": len(summary["failures"]),
        "mean_iou": summary["metrics"]["aligned_iou"]["mean"],
        "mean_quality": summary["metrics"]["quality_score"]["mean"],
    }, ensure_ascii=False, indent=2))
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
