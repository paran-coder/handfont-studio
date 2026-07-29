from __future__ import annotations

from .models import HangulDecomposition, NormalizedBox

S_BASE = 0xAC00
S_END = 0xD7A3
N_COUNT = 21 * 28
T_COUNT = 28

CHOSEONG = tuple("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
JUNGSEONG = tuple("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
JONGSEONG = (
    None, "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ",
    "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
)

VERTICAL_VOWELS = frozenset("ㅏㅐㅑㅒㅓㅔㅕㅖㅣ")
HORIZONTAL_VOWELS = frozenset("ㅗㅛㅜㅠㅡ")
COMPOUND_VOWELS = frozenset("ㅘㅙㅚㅝㅞㅟㅢ")


def is_modern_hangul_syllable(character: str) -> bool:
    return len(character) == 1 and S_BASE <= ord(character) <= S_END


def vowel_layout(vowel: str) -> str:
    if vowel in VERTICAL_VOWELS:
        return "vertical"
    if vowel in HORIZONTAL_VOWELS:
        return "horizontal"
    if vowel in COMPOUND_VOWELS:
        return "compound"
    raise ValueError(f"지원하지 않는 현대 한글 중성입니다: {vowel}")



def compose_syllable(choseong: str, jungseong: str, jongseong: str | None = None) -> str:
    try:
        l_index = CHOSEONG.index(choseong)
        v_index = JUNGSEONG.index(jungseong)
        t_index = JONGSEONG.index(jongseong)
    except ValueError as exc:
        raise ValueError("현대 한글 조합에 사용할 수 없는 자모입니다.") from exc
    return chr(S_BASE + (l_index * len(JUNGSEONG) + v_index) * T_COUNT + t_index)

def decompose_syllable(character: str) -> HangulDecomposition:
    if not is_modern_hangul_syllable(character):
        raise ValueError(f"현대 한글 완성형 음절이 아닙니다: {character!r}")
    s_index = ord(character) - S_BASE
    l_index = s_index // N_COUNT
    v_index = (s_index % N_COUNT) // T_COUNT
    t_index = s_index % T_COUNT
    initial = CHOSEONG[l_index]
    medial = JUNGSEONG[v_index]
    final = JONGSEONG[t_index]
    layout = vowel_layout(medial)
    has_final = t_index != 0
    suffix = "final" if has_final else "open"
    layout_class = f"{layout}-{suffix}"
    return HangulDecomposition(
        character=character,
        codepoint=ord(character),
        choseong=initial,
        jungseong=medial,
        jongseong=final,
        choseong_index=l_index,
        jungseong_index=v_index,
        jongseong_index=t_index,
        vowel_layout=layout,
        has_final=has_final,
        layout_class=layout_class,
        choseong_form=f"L:{initial}:{layout}:{suffix}",
        jungseong_form=f"V:{medial}:{layout}:{suffix}",
        jongseong_form=f"T:{final}:{layout}" if final else None,
    )


def layout_regions(decomposition: HangulDecomposition) -> dict[str, NormalizedBox]:
    """Return intentionally overlapping position regions inside a glyph ink bbox.

    These are layout priors for later handwriting segmentation, not claims that
    every font keeps each jamo inside a perfectly separated rectangle.
    """
    layout = decomposition.vowel_layout
    final = decomposition.has_final
    if layout == "vertical" and not final:
        return {
            "choseong": NormalizedBox(0.00, 0.00, 0.58, 1.00),
            "jungseong": NormalizedBox(0.42, 0.00, 1.00, 1.00),
        }
    if layout == "vertical" and final:
        return {
            "choseong": NormalizedBox(0.00, 0.00, 0.58, 0.72),
            "jungseong": NormalizedBox(0.42, 0.00, 1.00, 0.72),
            "jongseong": NormalizedBox(0.04, 0.58, 0.96, 1.00),
        }
    if layout == "horizontal" and not final:
        return {
            "choseong": NormalizedBox(0.00, 0.00, 1.00, 0.58),
            "jungseong": NormalizedBox(0.00, 0.42, 1.00, 1.00),
        }
    if layout == "horizontal" and final:
        return {
            "choseong": NormalizedBox(0.00, 0.00, 1.00, 0.46),
            "jungseong": NormalizedBox(0.00, 0.30, 1.00, 0.76),
            "jongseong": NormalizedBox(0.04, 0.62, 0.96, 1.00),
        }
    if layout == "compound" and not final:
        return {
            "choseong": NormalizedBox(0.00, 0.00, 0.58, 0.70),
            "jungseong": NormalizedBox(0.36, 0.00, 1.00, 1.00),
        }
    return {
        "choseong": NormalizedBox(0.00, 0.00, 0.58, 0.58),
        "jungseong": NormalizedBox(0.34, 0.00, 1.00, 0.78),
        "jongseong": NormalizedBox(0.04, 0.64, 0.96, 1.00),
    }
