from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import EmptyMaskError, VectorizerError
from .models import VectorizeOptions
from .pipeline import vectorize_mask


def _options(args: argparse.Namespace) -> VectorizeOptions:
    return VectorizeOptions(
        threshold=args.threshold,
        minimum_component_area=args.min_area,
        close_kernel=args.close_kernel,
        simplify_tolerance=args.simplify,
        corner_angle_degrees=args.corner_angle,
        smoothing_radius=args.smoothing,
        coordinate_precision=args.precision,
        target_raster_iou=args.target_iou,
        max_refinements=args.max_refinements,
    )


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--threshold", type=int, choices=range(0, 256), metavar="0-255")
    parser.add_argument("--min-area", type=int, default=12)
    parser.add_argument("--close-kernel", type=int, default=3)
    parser.add_argument("--simplify", type=float, default=0.00085)
    parser.add_argument("--corner-angle", type=float, default=110.0)
    parser.add_argument("--smoothing", type=float, default=0.05)
    parser.add_argument("--precision", type=int, default=2, choices=range(0, 6))
    parser.add_argument("--target-iou", type=float, default=0.90)
    parser.add_argument("--max-refinements", type=int, default=3)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handfont-glyph-vectorizer",
        description="HandFont Studio 잉크 마스크 SVG 베지어 윤곽선 변환 PoC",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("vectorize", help="단일 잉크 마스크를 벡터화합니다.")
    single.add_argument("--input", required=True, type=Path)
    single.add_argument("--output", required=True, type=Path)
    single.add_argument("--title")
    _add_common(single)

    batch = subparsers.add_parser("batch", help="폴더 아래 ink-mask.png 파일을 일괄 벡터화합니다.")
    batch.add_argument("--input-dir", required=True, type=Path)
    batch.add_argument("--output", required=True, type=Path)
    batch.add_argument("--pattern", default="**/ink-mask.png")
    _add_common(batch)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "vectorize":
            result = vectorize_mask(args.input, args.output, _options(args), title=args.title)
            print(json.dumps({
                "ok": True,
                "output_dir": str(result.output_dir),
                "svg": str(result.svg_path),
                "metadata": str(result.metadata_path),
                "raster_iou": round(result.iou, 6),
                "contours": result.contour_count,
                "node_reduction_ratio": round(result.node_reduction_ratio, 6),
            }, ensure_ascii=False, indent=2))
            return 0

        input_dir: Path = args.input_dir
        candidates = sorted(input_dir.glob(args.pattern))
        results = []
        skipped = []
        failures = []
        for path in candidates:
            relative_parent = path.parent.relative_to(input_dir)
            output_dir = args.output / relative_parent
            try:
                result = vectorize_mask(path, output_dir, _options(args), title=path.parent.name)
                results.append({
                    "input": str(path),
                    "output": str(result.output_dir),
                    "iou": round(result.iou, 6),
                    "contours": result.contour_count,
                })
            except EmptyMaskError as error:
                skipped.append({"input": str(path), "reason": str(error)})
            except VectorizerError as error:
                failures.append({"input": str(path), "error": str(error)})
        summary = {
            "ok": len(failures) == 0,
            "found": len(candidates),
            "processed": len(results),
            "skipped": len(skipped),
            "failed": len(failures),
            "results": results,
            "skipped_items": skipped,
            "failures": failures,
        }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "batch-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if not failures else 2
    except VectorizerError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except Exception as error:
        print(json.dumps({"ok": False, "error": f"예상하지 못한 오류: {error}"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
