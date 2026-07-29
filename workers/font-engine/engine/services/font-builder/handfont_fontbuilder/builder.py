from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fontTools.agl import UV2AGL
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.timeTools import timestampSinceEpoch
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.O_S_2f_2 import calcCodePageRanges, intersectUnicodeRanges

from .manifest import load_manifest
from .models import FontBuildOptions, GlyphBuildRecord
from .svg_outline import build_true_type_glyph


REQUIRED_TABLES = {"cmap", "glyf", "head", "hhea", "hmtx", "maxp", "name", "OS/2", "post", "loca"}


def _glyph_name(codepoint: int) -> str:
    return UV2AGL.get(codepoint, f"uni{codepoint:04X}" if codepoint <= 0xFFFF else f"u{codepoint:05X}")


def _empty_glyph():
    return TTGlyphPen(None).glyph()


def _notdef_glyph():
    pen = TTGlyphPen(None)
    pen.moveTo((60, 0))
    pen.lineTo((540, 0))
    pen.lineTo((540, 700))
    pen.lineTo((60, 700))
    pen.closePath()
    pen.moveTo((140, 100))
    pen.lineTo((140, 600))
    pen.lineTo((460, 600))
    pen.lineTo((460, 100))
    pen.closePath()
    return pen.glyph()


def _name_table(options: FontBuildOptions) -> dict[str, str]:
    ps_family = "".join(part for part in options.family_name.replace("-", " ").split() if part.isalnum())
    ps_style = "".join(part for part in options.style_name.replace("-", " ").split() if part.isalnum())
    return {
        "familyName": options.family_name,
        "styleName": options.style_name,
        "uniqueFontIdentifier": f"HandFontStudio:{options.family_name}:{options.style_name}:{options.version}",
        "fullName": f"{options.family_name} {options.style_name}",
        "psName": f"{ps_family}-{ps_style}",
        "version": f"Version {options.version}",
        "manufacturer": "HandFont Studio",
        "designer": "HandFont Studio user",
        "description": "HandFont Studio SVG-to-TTF proof-of-concept font with Hangul support.",
        "licenseDescription": "Prototype output for evaluation.",
    }


def _bitfields(bits: set[int], field_count: int) -> list[int]:
    fields = [0] * field_count
    for bit in bits:
        if 0 <= bit < field_count * 32:
            fields[bit // 32] |= 1 << (bit % 32)
    return fields


def _filename(options: FontBuildOptions) -> str:
    if options.output_basename:
        stem = options.output_basename
    else:
        stem = "".join(part for part in options.family_name.replace("-", " ").split() if part.isalnum())
        style = "".join(part for part in options.style_name.replace("-", " ").split() if part.isalnum())
        stem = f"{stem}-{style}"
    return f"{stem}.ttf"


def _configure_os2_ranges(font, codepoints: set[int]) -> dict[str, list[int]]:
    unicode_bits = intersectUnicodeRanges(codepoints)
    codepage_bits = calcCodePageRanges(codepoints)
    if any(0x20 <= cp <= 0x7E for cp in codepoints):
        codepage_bits.add(0)
    if any(0xAC00 <= cp <= 0xD7A3 or 0x3130 <= cp <= 0x318F for cp in codepoints):
        codepage_bits.add(19)
    unicode_fields = _bitfields(unicode_bits, 4)
    codepage_fields = _bitfields(codepage_bits, 2)
    os2 = font["OS/2"]
    for index, value in enumerate(unicode_fields, start=1):
        setattr(os2, f"ulUnicodeRange{index}", value)
    for index, value in enumerate(codepage_fields, start=1):
        setattr(os2, f"ulCodePageRange{index}", value)
    return {
        "unicode_range_bits": sorted(unicode_bits),
        "codepage_range_bits": sorted(codepage_bits),
        "unicode_range_fields": unicode_fields,
        "codepage_range_fields": codepage_fields,
    }


def build_font(manifest_path: Path, output_dir: Path, options: FontBuildOptions) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = load_manifest(manifest_path)

    glyph_order = [".notdef", "space"]
    glyphs = {".notdef": _notdef_glyph(), "space": _empty_glyph()}
    metrics: dict[str, tuple[int, int]] = {
        ".notdef": (600, 60),
        "space": (options.space_width, 0),
    }
    cmap = {0x20: "space"}
    records: list[GlyphBuildRecord] = []

    for source in sources:
        name = _glyph_name(source.codepoint)
        if name in glyphs:
            name = f"uni{source.codepoint:04X}"
        glyph, record = build_true_type_glyph(source, options, name)
        glyph_order.append(name)
        glyphs[name] = glyph
        metrics[name] = (record.advance_width, record.left_side_bearing)
        cmap[source.codepoint] = name
        records.append(record)

    fb = FontBuilder(options.units_per_em, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs, calcGlyphBounds=True)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=options.ascender, descent=options.descender, lineGap=options.line_gap)
    fb.setupNameTable(_name_table(options))
    fb.setupOS2(
        sTypoAscender=options.ascender,
        sTypoDescender=options.descender,
        sTypoLineGap=options.line_gap,
        usWinAscent=options.ascender,
        usWinDescent=abs(options.descender),
        sxHeight=options.x_height,
        sCapHeight=options.cap_height,
        usWeightClass=400,
        usWidthClass=5,
        fsSelection=0x40,
        achVendID="HFST",
        ulCodePageRange1=1,
        ulCodePageRange2=0,
    )
    fb.setupPost(keepGlyphNames=False)
    fb.setupMaxp()
    fixed_date = datetime(2026, 7, 28, tzinfo=timezone.utc).timestamp()
    fb.setupHead(created=timestampSinceEpoch(fixed_date), modified=timestampSinceEpoch(fixed_date))
    fb.font["head"].fontRevision = 1.005
    fb.setupDummyDSIG()

    range_report = _configure_os2_ranges(fb.font, set(cmap))

    filename = _filename(options)
    font_path = output_dir / filename
    fb.save(font_path)

    reopened = TTFont(font_path, recalcBBoxes=False, recalcTimestamp=False)
    missing_tables = sorted(REQUIRED_TABLES.difference(reopened.keys()))
    mapped = reopened.getBestCmap() or {}
    bounds_violations = []
    glyf = reopened["glyf"]
    for record in records:
        glyph = glyf[record.glyph_name]
        if glyph.numberOfContours == 0:
            bounds_violations.append({"glyph": record.glyph_name, "reason": "empty"})
            continue
        if glyph.yMin < options.descender - 10 or glyph.yMax > options.ascender + 10:
            bounds_violations.append(
                {"glyph": record.glyph_name, "yMin": glyph.yMin, "yMax": glyph.yMax, "reason": "vertical-range"}
            )
    reopened.close()

    digest = hashlib.sha256(font_path.read_bytes()).hexdigest()
    report = {
        "schema_version": "1.6.0",
        "font": filename,
        "sha256": digest,
        "family_name": options.family_name,
        "style_name": options.style_name,
        "units_per_em": options.units_per_em,
        "glyph_count": len(glyph_order),
        "mapped_codepoints": len(mapped),
        "input_glyphs": len(sources),
        "hangul_syllable_count": sum(0xAC00 <= source.codepoint <= 0xD7A3 for source in sources),
        "compatibility_jamo_count": sum(0x3130 <= source.codepoint <= 0x318F for source in sources),
        **range_report,
        "required_tables": sorted(REQUIRED_TABLES),
        "missing_tables": missing_tables,
        "bounds_violations": bounds_violations,
        "metrics": [asdict(record) for record in records],
    }
    (output_dir / "font-build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "glyph-metrics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(records[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)
    (output_dir / f"{filename}.sha256").write_text(f"{digest}  {filename}\n", encoding="utf-8")
    return report
