from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import SessionOptions
from .field_validation import FieldOptions, preflight_capture_session
from .field_synthetic import generate_field_benchmark
from .session import process_capture_session
from .synthetic import generate_benchmark_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="handfont-capture", description="HandFont Studio 촬영본 수집·페이지 식별 서비스")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="촬영 이미지 폴더를 처리합니다.")
    ingest.add_argument("--input", required=True, action="append", type=Path)
    ingest.add_argument("--output", required=True, type=Path)
    ingest.add_argument("--manual-corners", type=Path)
    ingest.add_argument("--dpi", type=int, default=150, choices=(150, 200, 300, 400))
    ingest.add_argument("--no-vectorize", action="store_true")
    ingest.add_argument("--vectorize-limit", type=int, default=64)
    ingest.add_argument("--min-page-confidence", type=float, default=0.35)

    preflight = subparsers.add_parser("preflight", help="촬영 이미지의 현장 품질을 사전 검사합니다.")
    preflight.add_argument("--input", required=True, action="append", type=Path)
    preflight.add_argument("--output", required=True, type=Path)
    preflight.add_argument("--manual-corners", type=Path)
    preflight.add_argument("--dpi", type=int, default=150, choices=(150, 200, 300, 400))
    preflight.add_argument("--data-origin", choices=("real", "synthetic"), default="real")

    field_benchmark = subparsers.add_parser("field-benchmark", help="합성 현장 품질 벤치마크를 생성하고 검사합니다.")
    field_benchmark.add_argument("--output", required=True, type=Path)
    field_benchmark.add_argument("--seed", type=int, default=20260729)
    field_benchmark.add_argument("--count-per-class", type=int, default=18)

    synthetic = subparsers.add_parser("generate-synthetic", help="합성 촬영 세션을 생성합니다.")
    synthetic.add_argument("--output", required=True, type=Path)
    synthetic.add_argument("--seed", type=int, default=20260728)
    synthetic.add_argument("--dpi", type=int, default=150)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "field-benchmark":
            result = generate_field_benchmark(args.output, seed=args.seed, count_per_class=args.count_per_class)
            print(json.dumps({"ok": True, "summary": str(args.output / "benchmark-summary.json"), **result}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "preflight":
            summary = preflight_capture_session(
                args.input,
                args.output,
                FieldOptions(dpi=args.dpi, data_origin=args.data_origin),
                manual_corners_path=args.manual_corners,
            )
            print(json.dumps({"ok": summary["session_status"] in {"accept", "review"}, "status": summary["session_status"], "summary": str(args.output / "preflight-report.json"), "missing_pages": summary["missing_pages"]}, ensure_ascii=False, indent=2))
            return 0 if summary["session_status"] in {"accept", "review"} else 2
        if args.command == "generate-synthetic":
            result = generate_benchmark_session(args.output, seed=args.seed, dpi=args.dpi)
            print(json.dumps({"ok": True, "photos": str(result["photos"]), "manual_corners": str(result["manual_corners"])}, ensure_ascii=False, indent=2))
            return 0
        summary = process_capture_session(
            args.input,
            args.output,
            SessionOptions(
                dpi=args.dpi,
                vectorize=not args.no_vectorize,
                vectorize_limit=args.vectorize_limit,
                min_page_confidence=args.min_page_confidence,
            ),
            manual_corners_path=args.manual_corners,
        )
        print(json.dumps({"ok": summary["complete"], "summary": str(args.output / "session-summary.json"), "selected_pages": summary["selected_pages"], "missing_pages": summary["missing_pages"]}, ensure_ascii=False, indent=2))
        return 0 if summary["complete"] else 2
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
