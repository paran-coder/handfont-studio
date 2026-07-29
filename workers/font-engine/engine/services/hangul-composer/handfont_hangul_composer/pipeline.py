from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from handfont_hangul.dataset import find_reference_font, render_character
from handfont_hangul.decomposition import decompose_syllable

from .benchmark import select_benchmark_characters
from .composer import HangulComposer
from .library import TemplateLibrary
from .models import ComposerOptions
from .quality import evaluate


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_benchmark(
    position_map: Path,
    source_masks: Path,
    output_dir: Path,
    vectorizer_root: Path,
    font_builder_root: Path | None = None,
    reference_font: Path | None = None,
    limit: int = 500,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    library_dir = output_dir / "template-library"
    generated_dir = output_dir / "generated"
    vector_dir = output_dir / "vectorized"
    generated_dir.mkdir(exist_ok=True)
    vector_dir.mkdir(exist_ok=True)

    library = TemplateLibrary.build(position_map, source_masks, library_dir)
    composer = HangulComposer(library, ComposerOptions())
    position_data = json.loads(position_map.read_text(encoding="utf-8"))
    representative = {entry["character"] for entry in position_data["entries"]}
    selected = select_benchmark_characters(representative, set(library.records))[:limit]
    if len(selected) != limit:
        raise ValueError(f"검증 음절 수가 부족합니다: {len(selected)} / {limit}")

    sys.path.insert(0, str(vectorizer_root))
    from handfont_vectorizer.geometry import extract_vector_contours
    from handfont_vectorizer.models import VectorizeOptions
    from handfont_vectorizer.quality import mask_iou, rasterize_svg
    from handfont_vectorizer.svg import build_svg

    reference = reference_font or find_reference_font()
    rows: list[dict] = []
    glyph_manifest = []
    failures = []
    for index, character in enumerate(selected, start=1):
        slug = f"U+{ord(character):04X}"
        item_dir = generated_dir / slug
        item_dir.mkdir(exist_ok=True)
        try:
            mask, layers, metadata = composer.compose(character)
            reference_mask = render_character(character, reference)
            quality = evaluate(mask, layers, reference_mask)
            mask_path = item_dir / "composed-mask.png"
            reference_path = item_dir / "reference-mask.png"
            overlay_path = item_dir / "comparison-overlay.png"
            cv2.imwrite(str(mask_path), mask)
            cv2.imwrite(str(reference_path), reference_mask)
            overlay = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
            overlay[:, :, 1] = reference_mask
            overlay[:, :, 2] = mask
            cv2.imwrite(str(overlay_path), overlay)
            metadata["quality"] = quality
            _write_json(item_dir / "composition.json", metadata)
            vector_result = _fast_vectorize(
                mask,
                vector_dir / slug,
                title=f"{character} {slug} composed",
                extract_vector_contours=extract_vector_contours,
                build_svg=build_svg,
                rasterize_svg=rasterize_svg,
                mask_iou=mask_iou,
                VectorizeOptions=VectorizeOptions,
            )
            d = decompose_syllable(character)
            row = {
                "index": index,
                "character": character,
                "codepoint": slug,
                "layout_class": d.layout_class,
                "exact_components": metadata["resolution"]["exact_components"],
                "fallback_components": metadata["resolution"]["fallback_components"],
                **quality,
                "vector_iou": round(vector_result["iou"], 6),
                "vector_contours": vector_result["contour_count"],
                "node_reduction_ratio": round(vector_result["node_reduction_ratio"], 6),
            }
            rows.append(row)
            glyph_manifest.append(
                {
                    "character": character,
                    "codepoint": ord(character),
                    "category": "한글-자동조합",
                    "cell_id": f"generated-{index:03d}",
                    "svg": str(vector_result["svg_path"].relative_to(output_dir)),
                    "metadata": str(vector_result["metadata_path"].relative_to(output_dir)),
                }
            )
        except Exception as exc:
            failures.append({"character": character, "codepoint": slug, "error": str(exc)})

    manifest = {
        "schema_version": "1.7.0",
        "source_type": "representative-syllable-composition",
        "requested_glyphs": limit,
        "generated_glyphs": len(glyph_manifest),
        "failures": failures,
        "glyphs": glyph_manifest,
    }
    _write_json(output_dir / "composed-glyph-manifest.json", manifest)
    if rows:
        fieldnames = list(rows[0].keys())
        with (output_dir / "benchmark-results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    else:
        (output_dir / "benchmark-results.csv").write_text("", encoding="utf-8")

    numeric = lambda key: np.array([float(row[key]) for row in rows], dtype=float)
    layout_counts = Counter(row["layout_class"] for row in rows)
    empty_stats = {"minimum": 0.0, "p10": 0.0, "median": 0.0, "mean": 0.0, "p90": 0.0, "maximum": 0.0}
    stat_for = lambda key: _stats(numeric(key)) if rows else dict(empty_stats)
    summary = {
        "schema_version": "1.7.0",
        "reference_font": reference.name,
        "representative_input_count": len(representative),
        "template_form_count": len(library.records),
        "benchmark_requested": limit,
        "benchmark_generated": len(rows),
        "failures": failures,
        "layout_counts": dict(sorted(layout_counts.items())),
        "exact_only_glyphs": sum(row["fallback_components"] == 0 for row in rows),
        "glyphs_with_fallback": sum(row["fallback_components"] > 0 for row in rows),
        "fallback_component_total": sum(row["fallback_components"] for row in rows),
        "review_count": sum(row["status"] == "review" for row in rows),
        "overflow_count": sum(bool(row["overflow"]) for row in rows),
        "metrics": {
            "aligned_iou": stat_for("aligned_iou"),
            "quality_score": stat_for("quality_score"),
            "normalized_chamfer": stat_for("normalized_chamfer"),
            "density_ratio": stat_for("density_ratio"),
            "max_pair_overlap_ratio": stat_for("max_pair_overlap_ratio"),
            "vector_iou": stat_for("vector_iou"),
            "node_reduction_ratio": stat_for("node_reduction_ratio"),
        },
        "worst_20": sorted(rows, key=lambda row: (row["quality_score"], row["aligned_iou"]))[:20],
        "best_20": sorted(rows, key=lambda row: (-row["quality_score"], -row["aligned_iou"]))[:20],
    }
    _write_json(output_dir / "benchmark-summary.json", summary)

    font_report = None
    if font_builder_root is not None and not failures:
        sys.path.insert(0, str(font_builder_root))
        from handfont_fontbuilder.builder import build_font
        from handfont_fontbuilder.models import FontBuildOptions
        from handfont_fontbuilder.validation import validate_and_render

        font_dir = output_dir / "internal-font"
        font_report = build_font(
            output_dir / "composed-glyph-manifest.json",
            font_dir,
            FontBuildOptions(
                family_name="HandFont Compose 500 PoC",
                style_name="Regular",
                version="1.7.0",
                output_basename="HandFont-Compose500-PoC",
            ),
        )
        font_path = font_dir / font_report["font"]
        validation = validate_and_render(font_path, font_dir)
        summary["font_build"] = font_report
        summary["font_validation"] = validation
        _write_json(output_dir / "benchmark-summary.json", summary)
    return summary



def _fast_vectorize(mask, output_dir: Path, *, title: str, extract_vector_contours, build_svg, rasterize_svg, mask_iou, VectorizeOptions) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    binary = (mask > 0).astype(np.uint8) * 255
    height, width = binary.shape
    best = None
    for tolerance in (0.00055, 0.00036):
        options = VectorizeOptions(
            minimum_component_area=4,
            close_kernel=1,
            simplify_tolerance=tolerance,
            corner_angle_degrees=112.0,
            smoothing_radius=0.035,
            minimum_foreground_ratio=0.00003,
            target_raster_iou=0.90,
            max_refinements=0,
        )
        contours = extract_vector_contours(binary, options)
        svg = build_svg(contours, width, height, title=title)
        raster = rasterize_svg(svg, width, height)
        iou = float(mask_iou(binary, raster))
        original_nodes = sum(len(contour.original_points) for contour in contours)
        simplified_nodes = sum(len(contour.simplified_points) for contour in contours)
        reduction = 1.0 - simplified_nodes / max(original_nodes, 1)
        candidate = (iou, contours, svg, reduction, tolerance)
        if best is None or iou > best[0]:
            best = candidate
        if iou >= 0.90:
            break
    assert best is not None
    iou, contours, svg, reduction, tolerance = best
    svg_path = output_dir / "glyph.svg"
    metadata_path = output_dir / "metadata.json"
    svg_path.write_text(svg, encoding="utf-8")
    metadata = {
        "schema_version": "1.7.0-fast",
        "normalization": {"input_shape": [height, width], "output_shape": [height, width]},
        "options": {"simplify_tolerance_effective": tolerance, "target_raster_iou": 0.90},
        "summary": {
            "contours": len(contours),
            "outer_contours": sum(not contour.is_hole for contour in contours),
            "hole_contours": sum(contour.is_hole for contour in contours),
            "node_reduction_ratio": round(reduction, 6),
            "raster_iou": round(iou, 6),
            "status": "ok" if iou >= 0.90 else "review",
        },
        "contours": [
            {
                "index": contour.index,
                "parent": contour.parent,
                "depth": contour.depth,
                "is_hole": contour.is_hole,
                "area": round(contour.area, 3),
                "original_points": len(contour.original_points),
                "simplified_points": len(contour.simplified_points),
                "path_commands": contour.path_commands,
            }
            for contour in contours
        ],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "svg_path": svg_path,
        "metadata_path": metadata_path,
        "iou": iou,
        "contour_count": len(contours),
        "node_reduction_ratio": reduction,
    }

def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "minimum": round(float(np.min(values)), 6),
        "p10": round(float(np.percentile(values, 10)), 6),
        "median": round(float(np.median(values)), 6),
        "mean": round(float(np.mean(values)), 6),
        "p90": round(float(np.percentile(values, 90)), 6),
        "maximum": round(float(np.max(values)), 6),
    }
