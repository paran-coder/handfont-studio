from __future__ import annotations

import math
import unicodedata

from .models import FontBuildOptions, VerticalPlacement


DESCENDERS = set("gjpqy")
ASCENDERS = set("bdfhklt")


def is_hangul_syllable(character: str) -> bool:
    return len(character) == 1 and 0xAC00 <= ord(character) <= 0xD7A3


def is_compatibility_jamo(character: str) -> bool:
    return len(character) == 1 and 0x3130 <= ord(character) <= 0x318F


def vertical_placement(character: str, options: FontBuildOptions) -> VerticalPlacement:
    if is_hangul_syllable(character) or is_compatibility_jamo(character):
        return VerticalPlacement(760, -40, "hangul-square")
    if character.isupper():
        return VerticalPlacement(options.cap_height, 0, "cap")
    if character.islower():
        if character in DESCENDERS:
            return VerticalPlacement(options.x_height, options.descender, "x-descender")
        if character in ASCENDERS:
            return VerticalPlacement(options.cap_height, 0, "ascender")
        return VerticalPlacement(options.x_height, 0, "x-height")
    if character.isdigit():
        return VerticalPlacement(options.cap_height, 0, "lining-digit")

    rules: dict[str, VerticalPlacement] = {
        ".": VerticalPlacement(120, 0, "low-mark"),
        ",": VerticalPlacement(120, -150, "low-descender-mark"),
        ":": VerticalPlacement(500, 100, "mid-mark"),
        ";": VerticalPlacement(500, -120, "mid-descender-mark"),
        "'": VerticalPlacement(700, 450, "high-mark"),
        '"': VerticalPlacement(700, 450, "high-mark"),
        "-": VerticalPlacement(330, 230, "center-mark"),
        "_": VerticalPlacement(-40, -120, "baseline-mark"),
        "+": VerticalPlacement(560, 100, "math-mark"),
        "=": VerticalPlacement(480, 160, "math-mark"),
        "!": VerticalPlacement(700, 0, "full-mark"),
        "?": VerticalPlacement(700, 0, "full-mark"),
        "(": VerticalPlacement(750, -200, "delimiter"),
        ")": VerticalPlacement(750, -200, "delimiter"),
        "[": VerticalPlacement(750, -200, "delimiter"),
        "]": VerticalPlacement(750, -200, "delimiter"),
        "{": VerticalPlacement(750, -200, "delimiter"),
        "}": VerticalPlacement(750, -200, "delimiter"),
        "/": VerticalPlacement(750, -200, "delimiter"),
        "\\": VerticalPlacement(750, -200, "delimiter"),
        "@": VerticalPlacement(700, -80, "wide-symbol"),
        "#": VerticalPlacement(700, 0, "full-symbol"),
        "&": VerticalPlacement(700, 0, "full-symbol"),
        "%": VerticalPlacement(700, 0, "full-symbol"),
        "$": VerticalPlacement(750, -80, "currency-symbol"),
        "₩": VerticalPlacement(700, 0, "currency-symbol"),
    }
    return rules.get(character, VerticalPlacement(options.cap_height, 0, "symbol"))


def side_bearings(character: str, options: FontBuildOptions) -> tuple[int, int, int]:
    if is_hangul_syllable(character) or is_compatibility_jamo(character):
        return 60, 60, options.units_per_em
    narrow = set("Iijl1.,:;'!|()[]{}")
    wide = set("MWmw@%&")
    if character in narrow:
        return 45, 45, 220
    if character in wide:
        return 55, 55, 520
    if unicodedata.category(character).startswith("P"):
        return 50, 50, 260
    return options.default_lsb, options.default_rsb, 320


def calculate_scale_and_advance(
    character: str,
    source_bbox: tuple[float, float, float, float],
    options: FontBuildOptions,
) -> tuple[float, int, int, int, VerticalPlacement]:
    x_min, y_min, x_max, y_max = source_bbox
    width = max(x_max - x_min, 1.0)
    height = max(y_max - y_min, 1.0)
    placement = vertical_placement(character, options)
    target_height = max(placement.top - placement.bottom, 1)

    if is_hangul_syllable(character) or is_compatibility_jamo(character):
        scale = min(target_height / height, 880.0 / width)
        outline_width = int(math.ceil(width * scale))
        advance = options.units_per_em
        lsb = max(40, (advance - outline_width) // 2)
        rsb_actual = advance - lsb - outline_width
        return scale, lsb, rsb_actual, advance, placement

    lsb, rsb, minimum_advance = side_bearings(character, options)
    scale = target_height / height
    max_outline_width = options.units_per_em - lsb - rsb - 40
    if width * scale > max_outline_width:
        scale = max_outline_width / width
    outline_width = int(math.ceil(width * scale))
    advance = max(minimum_advance, lsb + outline_width + rsb)
    advance = int(math.ceil(advance / 10.0) * 10)
    rsb_actual = advance - lsb - outline_width
    return scale, lsb, rsb_actual, advance, placement
