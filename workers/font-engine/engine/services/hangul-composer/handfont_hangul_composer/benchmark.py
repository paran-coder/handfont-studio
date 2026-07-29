from __future__ import annotations

import hashlib
from collections import defaultdict

from handfont_hangul.decomposition import S_BASE, S_END, decompose_syllable


DEFAULT_QUOTAS = {
    "vertical-open": 80,
    "vertical-final": 100,
    "horizontal-open": 70,
    "horizontal-final": 90,
    "compound-open": 70,
    "compound-final": 90,
}


def _rank(character: str) -> bytes:
    return hashlib.blake2b(f"handfont-v1.7.0:{character}".encode("utf-8"), digest_size=12).digest()


def select_benchmark_characters(
    representative_characters: set[str],
    available_forms: set[str],
    quotas: dict[str, int] = DEFAULT_QUOTAS,
) -> list[str]:
    groups: dict[str, list[str]] = defaultdict(list)
    for codepoint in range(S_BASE, S_END + 1):
        character = chr(codepoint)
        if character in representative_characters:
            continue
        groups[decompose_syllable(character).layout_class].append(character)

    selected: list[str] = []
    for layout_class, quota in quotas.items():
        candidates = groups[layout_class]
        # Missing-position forms are sampled first so fallback behavior is explicitly measured.
        def key(character: str):
            d = decompose_syllable(character)
            forms = [d.choseong_form, d.jungseong_form] + ([d.jongseong_form] if d.jongseong_form else [])
            missing = sum(form not in available_forms for form in forms)
            return (-missing, _rank(character), ord(character))

        chosen = sorted(candidates, key=key)[:quota]
        selected.extend(chosen)
    return sorted(selected, key=ord)
