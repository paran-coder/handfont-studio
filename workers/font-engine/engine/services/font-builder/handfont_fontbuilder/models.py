from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontBuildOptions:
    family_name: str = "HandFont Studio PoC"
    style_name: str = "Regular"
    version: str = "1.6.0"
    units_per_em: int = 1000
    ascender: int = 800
    descender: int = -200
    line_gap: int = 200
    cap_height: int = 700
    x_height: int = 500
    default_lsb: int = 60
    default_rsb: int = 60
    space_width: int = 320
    output_basename: str | None = None


@dataclass(frozen=True)
class GlyphSource:
    character: str
    codepoint: int
    category: str
    svg_path: Path
    metadata_path: Path
    cell_id: str | None = None


@dataclass(frozen=True)
class VerticalPlacement:
    top: int
    bottom: int
    label: str


@dataclass(frozen=True)
class GlyphBuildRecord:
    character: str
    codepoint: int
    glyph_name: str
    category: str
    source_svg: str
    source_bbox: tuple[float, float, float, float]
    font_bbox: tuple[int, int, int, int]
    advance_width: int
    left_side_bearing: int
    right_side_bearing: int
    vertical_class: str
    scale: float
    contour_count: int
    hole_count: int
