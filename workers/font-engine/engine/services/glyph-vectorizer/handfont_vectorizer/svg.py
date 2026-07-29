from __future__ import annotations

import html

from .geometry import VectorContour


def build_svg(contours: list[VectorContour], width: int, height: int, *, title: str = "HandFont glyph") -> str:
    path_data = " ".join(contour.path_data for contour in contours)
    safe_title = html.escape(title)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{safe_title}">\n'
        f'  <title>{safe_title}</title>\n'
        f'  <path d="{path_data}" fill="#000000" fill-rule="evenodd" clip-rule="evenodd"/>\n'
        '</svg>\n'
    )
