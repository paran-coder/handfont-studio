from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen

from .errors import SvgOutlineError
from .metrics import calculate_scale_and_advance
from .models import FontBuildOptions, GlyphBuildRecord, GlyphSource


def _read_path_data(svg_path: Path) -> tuple[str, tuple[float, float, float, float]]:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    view_box = root.attrib.get("viewBox")
    if not view_box:
        raise SvgOutlineError(f"viewBox가 없습니다: {svg_path}")
    parts = [float(value) for value in view_box.replace(",", " ").split()]
    if len(parts) != 4:
        raise SvgOutlineError(f"viewBox 형식이 잘못되었습니다: {svg_path}")
    path_node = next((node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "path"), None)
    if path_node is None or not path_node.attrib.get("d"):
        raise SvgOutlineError(f"path d가 없습니다: {svg_path}")
    return path_node.attrib["d"], tuple(parts)  # type: ignore[return-value]


def _split_contours(path_data: str) -> list[RecordingPen]:
    recording = RecordingPen()
    parse_path(path_data, recording)
    contours: list[RecordingPen] = []
    current = RecordingPen()
    for operator, operands in recording.value:
        getattr(current, operator)(*operands)
        if operator in {"closePath", "endPath"}:
            contours.append(current)
            current = RecordingPen()
    if current.value:
        contours.append(current)
    return contours


def _source_bounds(contours: list[RecordingPen]) -> tuple[float, float, float, float]:
    pen = BoundsPen(None)
    for contour in contours:
        contour.replay(pen)
    if pen.bounds is None:
        raise SvgOutlineError("SVG 윤곽선의 경계를 계산할 수 없습니다.")
    return pen.bounds


def _hole_flags(metadata_path: Path, contour_count: int) -> list[bool]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    entries = metadata.get("contours", [])
    if len(entries) != contour_count:
        raise SvgOutlineError(
            f"SVG contour 수({contour_count})와 metadata contour 수({len(entries)})가 다릅니다: {metadata_path}"
        )
    return [bool(item.get("is_hole", False)) for item in entries]


def build_true_type_glyph(
    source: GlyphSource,
    options: FontBuildOptions,
    glyph_name: str,
) -> tuple[Glyph, GlyphBuildRecord]:
    path_data, _ = _read_path_data(source.svg_path)
    contours = _split_contours(path_data)
    if not contours:
        raise SvgOutlineError(f"윤곽선이 비어 있습니다: {source.svg_path}")
    source_bbox = _source_bounds(contours)
    holes = _hole_flags(source.metadata_path, len(contours))
    scale, lsb, rsb, advance, placement = calculate_scale_and_advance(source.character, source_bbox, options)
    x_min, y_min, x_max, y_max = source_bbox
    transform = (scale, 0.0, 0.0, -scale, lsb - x_min * scale, placement.top + y_min * scale)

    tt_pen = TTGlyphPen(None)
    rounded_pen = RoundingPen(tt_pen)
    for contour, is_hole in zip(contours, holes, strict=True):
        area_pen = AreaPen(None)
        contour.replay(TransformPen(area_pen, transform))
        should_be_positive = not is_hole
        has_positive_area = area_pen.value > 0
        destination = rounded_pen if has_positive_area == should_be_positive else ReverseContourPen(rounded_pen)
        contour.replay(TransformPen(destination, transform))
    glyph = tt_pen.glyph()

    font_width = int(round((x_max - x_min) * scale))
    actual_bottom = int(round(placement.top - (y_max - y_min) * scale))
    font_bbox = (
        lsb,
        actual_bottom,
        lsb + font_width,
        int(round(placement.top)),
    )
    record = GlyphBuildRecord(
        character=source.character,
        codepoint=source.codepoint,
        glyph_name=glyph_name,
        category=source.category,
        source_svg=str(source.svg_path),
        source_bbox=tuple(round(value, 3) for value in source_bbox),
        font_bbox=font_bbox,
        advance_width=advance,
        left_side_bearing=lsb,
        right_side_bearing=rsb,
        vertical_class=placement.label,
        scale=round(scale, 6),
        contour_count=len(contours),
        hole_count=sum(holes),
    )
    return glyph, record
