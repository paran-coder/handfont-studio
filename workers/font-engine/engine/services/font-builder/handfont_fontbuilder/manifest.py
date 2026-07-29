from __future__ import annotations

import json
from pathlib import Path

from .errors import ManifestError
from .models import GlyphSource


def load_manifest(path: Path) -> list[GlyphSource]:
    data = json.loads(path.read_text(encoding="utf-8"))
    glyphs = data.get("glyphs")
    if not isinstance(glyphs, list) or not glyphs:
        raise ManifestError("manifest의 glyphs가 비어 있습니다.")
    result: list[GlyphSource] = []
    seen: set[int] = set()
    for index, item in enumerate(glyphs):
        character = item.get("character")
        if not isinstance(character, str) or len(character) != 1:
            raise ManifestError(f"glyphs[{index}].character는 문자 1개여야 합니다.")
        codepoint = int(item.get("codepoint", ord(character)))
        if codepoint != ord(character):
            raise ManifestError(f"문자와 codepoint가 일치하지 않습니다: {character}")
        if codepoint in seen:
            raise ManifestError(f"중복 codepoint: U+{codepoint:04X}")
        seen.add(codepoint)
        svg_path = (path.parent / item["svg"]).resolve()
        metadata_path = (path.parent / item["metadata"]).resolve()
        if not svg_path.exists() or not metadata_path.exists():
            raise ManifestError(f"입력 파일이 없습니다: {svg_path} / {metadata_path}")
        result.append(
            GlyphSource(
                character=character,
                codepoint=codepoint,
                category=str(item.get("category", "unknown")),
                svg_path=svg_path,
                metadata_path=metadata_path,
                cell_id=item.get("cell_id"),
            )
        )
    return sorted(result, key=lambda item: item.codepoint)
