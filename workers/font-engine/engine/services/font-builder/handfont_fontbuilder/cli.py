from __future__ import annotations

import argparse
import json
from pathlib import Path

from .builder import build_font
from .models import FontBuildOptions
from .validation import validate_and_render


def main() -> int:
    parser = argparse.ArgumentParser(prog="handfont-font-builder")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="SVG manifest를 TTF로 빌드합니다.")
    build_parser.add_argument("--manifest", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--family-name", default="HandFont Studio PoC")
    build_parser.add_argument("--style-name", default="Regular")
    build_parser.add_argument("--output-basename")

    args = parser.parse_args()
    if args.command == "build":
        options = FontBuildOptions(
            family_name=args.family_name,
            style_name=args.style_name,
            output_basename=args.output_basename,
        )
        report = build_font(args.manifest, args.output, options)
        validation = validate_and_render(args.output / report["font"], args.output)
        print(json.dumps({"build": report, "validation": validation}, ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
