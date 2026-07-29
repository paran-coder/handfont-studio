from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class ComposerOptions:
    canvas_size: int = 480
    canonical_bbox: tuple[int, int, int, int] = (106, 96, 373, 384)
    fallback_inner_padding: float = 0.08
    natural_variation: float = 0.0
    random_seed: int = 1700
    target_vector_iou: float = 0.90


@dataclass
class TemplateRecord:
    form_id: str
    role: str
    jamo: str
    source_character: str
    source_codepoint: str
    source_region: tuple[int, int, int, int]
    candidate_count: int
    selection_method: str
    mask_path: Path
    exact_layout: str
    exact_state: str | None

    def to_dict(self, root: Path | None = None) -> dict:
        data = asdict(self)
        data["mask_path"] = str(self.mask_path.relative_to(root) if root else self.mask_path)
        data["source_region"] = list(self.source_region)
        return data


@dataclass
class ComponentUse:
    role: str
    requested_form: str
    resolved_form: str
    resolution: str
    source_character: str
    template_candidates: int
    overlap_pixels: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
