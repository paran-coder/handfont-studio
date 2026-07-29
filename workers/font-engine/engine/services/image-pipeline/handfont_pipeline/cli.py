from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, DEFAULT_MAPPING_PATH
from .errors import PipelineError
from .models import ProcessOptions
from .pipeline import process_page


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handfont-image-pipeline",
        description="HandFont Studio 템플릿 등록 마커 검출 및 글자 칸 추출 PoC",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    process = subparsers.add_parser("process", help="PDF 또는 이미지 한 페이지를 처리합니다.")
    process.add_argument("--input", required=True, type=Path, help="PNG/JPEG 또는 PDF 입력")
    process.add_argument("--output", required=True, type=Path, help="결과 폴더")
    process.add_argument("--template-page", required=True, type=int, choices=range(1, 10), metavar="1-9")
    process.add_argument("--pdf-page", type=int, help="PDF의 1부터 시작하는 페이지 번호")
    process.add_argument("--dpi", type=int, default=300, choices=(150, 200, 300, 400))
    process.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT_PATH)
    process.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING_PATH)
    process.add_argument("--blank-dir", type=Path, default=DEFAULT_BLANK_DIR)
    process.add_argument("--no-full-cells", action="store_true")
    process.add_argument("--no-writing-rois", action="store_true")
    process.add_argument("--no-masks", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "process":
            result = process_page(
                args.input,
                args.output,
                ProcessOptions(
                    template_page=args.template_page,
                    output_dpi=args.dpi,
                    save_full_cells=not args.no_full_cells,
                    save_writing_rois=not args.no_writing_rois,
                    save_masks=not args.no_masks,
                ),
                pdf_page=args.pdf_page,
                layout_path=args.layout,
                mapping_path=args.mapping,
                blank_dir=args.blank_dir,
            )
            print(
                json.dumps(
                    {
                        "ok": True,
                        "output_dir": str(result.output_dir),
                        "metadata": str(result.metadata_path),
                        "rectified": str(result.rectified_path),
                        "overlay": str(result.overlay_path),
                        "marker_confidence": round(result.marker_confidence, 6),
                        "cells_written": result.cells_written,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
    except PipelineError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except Exception as error:  # defensive CLI boundary
        print(json.dumps({"ok": False, "error": f"예상하지 못한 오류: {error}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
