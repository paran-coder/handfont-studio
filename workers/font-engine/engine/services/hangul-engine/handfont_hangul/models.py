from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class NormalizedBox:
    x0: float
    y0: float
    x1: float
    y1: float

    def clamp(self) -> "NormalizedBox":
        return NormalizedBox(
            max(0.0, min(1.0, self.x0)),
            max(0.0, min(1.0, self.y0)),
            max(0.0, min(1.0, self.x1)),
            max(0.0, min(1.0, self.y1)),
        )

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class HangulDecomposition:
    character: str
    codepoint: int
    choseong: str
    jungseong: str
    jongseong: str | None
    choseong_index: int
    jungseong_index: int
    jongseong_index: int
    vowel_layout: str
    has_final: bool
    layout_class: str
    choseong_form: str
    jungseong_form: str
    jongseong_form: str | None
