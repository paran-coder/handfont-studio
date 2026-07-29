from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
from typing import Any

from .utils import read_json, write_json


def build_captured_manifest(ingest_dir: Path, output_path: Path) -> dict[str, Any]:
    summary = read_json(ingest_dir / "session-summary.json")
    glyphs: list[dict[str, Any]] = []
    seen: set[int] = set()
    skipped: list[dict[str, Any]] = []
    for record in summary.get("vectorization", {}).get("records", []):
        character = record.get("character", "")
        if not isinstance(character, str) or len(character) != 1:
            skipped.append({"cell_id": record.get("cell_id"), "reason": "invalid-character"})
            continue
        codepoint = ord(character)
        if codepoint in seen:
            skipped.append({"cell_id": record.get("cell_id"), "character": character, "reason": "duplicate-codepoint"})
            continue
        svg_path = ingest_dir / record["svg"]
        metadata_path = svg_path.parent / "metadata.json"
        if not svg_path.exists() or not metadata_path.exists():
            skipped.append({"cell_id": record.get("cell_id"), "character": character, "reason": "missing-vector-files"})
            continue
        seen.add(codepoint)
        glyphs.append({
            "character": character,
            "codepoint": codepoint,
            "category": "captured",
            "cell_id": record.get("cell_id"),
            "svg": os.path.relpath(svg_path, output_path.parent),
            "metadata": os.path.relpath(metadata_path, output_path.parent),
        })
    payload = {
        "schema_version": "2.1.0",
        "source_type": "captured-session",
        "glyph_count": len(glyphs),
        "skipped": skipped,
        "glyphs": sorted(glyphs, key=lambda item: item["codepoint"]),
    }
    write_json(output_path, payload)
    return payload


def export_representative_masks(ingest_dir: Path, position_map_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    position_map = read_json(position_map_path)
    entries_by_character = {entry["character"]: entry for entry in position_map["entries"]}
    required = set(entries_by_character)
    found: dict[str, Path] = {}
    page_metadata = sorted((ingest_dir / "pages").glob("page-*/metadata.json"))
    for metadata_path in page_metadata:
        metadata = read_json(metadata_path)
        page_dir = metadata_path.parent
        for cell in metadata.get("cells", []):
            character = cell.get("character", "")
            if character not in required or character in found:
                continue
            mask_rel = cell.get("files", {}).get("ink_mask")
            if not mask_rel:
                continue
            mask_path = page_dir / mask_rel
            if mask_path.exists():
                found[character] = mask_path
    copied = []
    for character in sorted(found, key=ord):
        target = output_dir / f"U+{ord(character):04X}.png"
        source = cv2.imread(str(found[character]), cv2.IMREAD_GRAYSCALE)
        if source is None:
            continue
        # Capture masks are writing-ROI sized, while the position map is defined on
        # the canonical 480 x 480 glyph canvas. Fit the observed ink into the
        # representative glyph box so all component regions share one coordinate system.
        binary = (source > 127).astype(np.uint8) * 255
        ys, xs = np.where(binary > 0)
        if len(xs) == 0:
            continue
        crop = binary[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        x0, y0, x1, y1 = map(int, entries_by_character[character].get("glyph_ink_bbox", [40, 40, 440, 440]))
        box_w, box_h = max(1, x1 - x0), max(1, y1 - y0)
        scale = min(box_w / max(1, crop.shape[1]), box_h / max(1, crop.shape[0]))
        width = max(1, int(round(crop.shape[1] * scale)))
        height = max(1, int(round(crop.shape[0] * scale)))
        resized = cv2.resize(crop, (width, height), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        resized = (resized > 96).astype(np.uint8) * 255
        canvas = np.zeros((480, 480), dtype=np.uint8)
        px = x0 + max(0, (box_w - width) // 2)
        py = y0 + max(0, (box_h - height) // 2)
        x_end = min(480, px + width)
        y_end = min(480, py + height)
        canvas[py:y_end, px:x_end] = resized[: y_end - py, : x_end - px]
        if not cv2.imwrite(str(target), canvas):
            raise OSError(f"정규화 마스크를 저장하지 못했습니다: {target}")
        copied.append({
            "character": character,
            "codepoint": f"U+{ord(character):04X}",
            "source": str(found[character]),
            "target": target.name,
            "source_shape": list(source.shape),
            "canonical_shape": [480, 480],
            "target_bbox": [x0, y0, x1, y1],
        })
    missing = sorted(required - set(found), key=ord)
    report = {
        "schema_version": "2.1.0",
        "required": len(required),
        "copied": len(copied),
        "missing_count": len(missing),
        "missing": [{"character": char, "codepoint": f"U+{ord(char):04X}"} for char in missing],
        "items": copied,
    }
    write_json(output_dir / "source-mask-report.json", report)
    return report


def merge_manifests(manifest_paths: list[Path], output_path: Path) -> dict[str, Any]:
    glyph_by_codepoint: dict[int, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    sources: list[str] = []
    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue
        data = read_json(manifest_path)
        sources.append(str(manifest_path))
        for item in data.get("glyphs", []):
            character = item["character"]
            codepoint = int(item.get("codepoint", ord(character)))
            svg_abs = (manifest_path.parent / item["svg"]).resolve()
            metadata_abs = (manifest_path.parent / item["metadata"]).resolve()
            normalized = {
                "character": character,
                "codepoint": codepoint,
                "category": item.get("category", "unknown"),
                "cell_id": item.get("cell_id"),
                "svg": os.path.relpath(svg_abs, output_path.parent),
                "metadata": os.path.relpath(metadata_abs, output_path.parent),
            }
            if codepoint in glyph_by_codepoint:
                conflicts.append({
                    "codepoint": f"U+{codepoint:04X}",
                    "kept": glyph_by_codepoint[codepoint].get("category"),
                    "discarded": normalized.get("category"),
                })
                continue
            glyph_by_codepoint[codepoint] = normalized
    glyphs = [glyph_by_codepoint[key] for key in sorted(glyph_by_codepoint)]
    payload = {
        "schema_version": "2.1.0",
        "source_type": "captured-plus-composed",
        "sources": sources,
        "glyph_count": len(glyphs),
        "conflicts": conflicts,
        "glyphs": glyphs,
    }
    write_json(output_path, payload)
    return payload
