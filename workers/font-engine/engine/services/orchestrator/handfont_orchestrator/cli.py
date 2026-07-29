from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import RunOptions
from .pilot import build_pilot_outputs
from .runner import run_pipeline


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True, action="append", type=Path, help="사진 파일 또는 폴더. 여러 번 지정할 수 있습니다.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manual-corners", type=Path)
    parser.add_argument("--data-origin", choices=("real", "synthetic"), default="real")
    parser.add_argument("--dpi", type=int, choices=(150, 200, 300, 400), default=150)
    parser.add_argument("--family-name", default="HandFont Studio")
    parser.add_argument("--style-name", default="Regular")
    parser.add_argument("--vectorize-limit", type=int, help="생략하면 모든 유효 셀을 벡터화합니다.")
    parser.add_argument("--allow-retake", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--keep-intermediate-font", action="store_true", help="개발 디버깅 전용. 공유 패키지에는 폰트 파일을 포함하지 마십시오.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="handfont-orchestrator", description="HandFont Studio v2.1.0 통합 파이프라인")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="촬영본부터 내부 폰트 검증까지 전체 파이프라인을 실행합니다.")
    _common_arguments(run)
    run.add_argument("--compose-limit", type=int, default=64)
    run.add_argument("--expected-pages", default="1,2,3,4,5,6,7,8,9", help="쉼표로 구분한 작성지 페이지")

    pilot = subparsers.add_parser("pilot", help="작성지 1~3페이지 파일럿 검증을 실행합니다.")
    _common_arguments(pilot)
    pilot.set_defaults(compose_limit=0, expected_pages="1,2,3")
    return parser


def _parse_pages(value: str) -> tuple[int, ...]:
    try:
        pages = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as error:
        raise ValueError("expected-pages는 쉼표로 구분한 정수여야 합니다.") from error
    return pages


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        expected_pages = _parse_pages(args.expected_pages)
        report = run_pipeline(
            args.input,
            args.output,
            RunOptions(
                dpi=args.dpi,
                data_origin=args.data_origin,
                family_name=args.family_name,
                style_name=args.style_name,
                vectorize_limit=args.vectorize_limit,
                compose_limit=args.compose_limit,
                allow_retake=args.allow_retake,
                resume=args.resume,
                keep_intermediate_font=args.keep_intermediate_font,
                expected_pages=expected_pages,
            ),
            manual_corners=args.manual_corners,
        )
        response = {
            "ok": report["status"] in {"completed", "review"},
            "status": report["status"],
            "report": str(args.output / "run-report.json"),
            "html": str(args.output / "run-report.html"),
        }
        if args.command == "pilot":
            pilot_report = build_pilot_outputs(args.output, expected_pages)
            response.update({
                "pilot_status": pilot_report["pilot_status"],
                "pilot_report": str(args.output / "pilot-report.json"),
                "pilot_html": str(args.output / "pilot-report.html"),
                "rewrite_priority": str(args.output / "rewrite-priority.csv"),
            })
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0 if report["status"] in {"completed", "review"} else 2
    except Exception as error:
        print(json.dumps({"ok": False, "error": f"{type(error).__name__}: {error}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
