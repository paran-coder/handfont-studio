from __future__ import annotations

import hashlib
from dataclasses import asdict

import cv2
import numpy as np

from handfont_hangul.decomposition import decompose_syllable, layout_regions

from .library import TemplateLibrary
from .models import ComponentUse, ComposerOptions


_LAYOUT_DISTANCE = {
    ("vertical", "vertical"): 0,
    ("horizontal", "horizontal"): 0,
    ("compound", "compound"): 0,
    ("vertical", "compound"): 1,
    ("compound", "vertical"): 1,
    ("horizontal", "compound"): 1,
    ("compound", "horizontal"): 1,
    ("vertical", "horizontal"): 2,
    ("horizontal", "vertical"): 2,
}


class HangulComposer:
    def __init__(self, library: TemplateLibrary, options: ComposerOptions = ComposerOptions()):
        self.library = library
        self.options = options

    def _requested_form(self, decomposition, role: str) -> str:
        return getattr(decomposition, f"{role}_form")

    def resolve_form(self, decomposition, role: str) -> tuple[str, str]:
        requested = self._requested_form(decomposition, role)
        if requested in self.library.records:
            return requested, "exact"
        jamo = getattr(decomposition, role)
        target_state = "final" if decomposition.has_final else "open"
        candidates: list[tuple[int, int, str]] = []
        for form_id, record in self.library.records.items():
            if record.role != role or record.jamo != jamo:
                continue
            distance = _LAYOUT_DISTANCE[(record.exact_layout, decomposition.vowel_layout)]
            state_penalty = 0
            if role != "jongseong" and record.exact_state != target_state:
                state_penalty = 1
            candidates.append((distance, state_penalty, form_id))
        if not candidates:
            raise KeyError(f"사용할 수 있는 위치형 템플릿이 없습니다: {requested}")
        _, _, resolved = min(candidates)
        return resolved, "fallback"

    def _target_region(self, decomposition, role: str) -> tuple[int, int, int, int]:
        gx0, gy0, gx1, gy1 = self.options.canonical_bbox
        normalized = layout_regions(decomposition)[role]
        width = gx1 - gx0
        height = gy1 - gy0
        return (
            int(round(gx0 + normalized.x0 * width)),
            int(round(gy0 + normalized.y0 * height)),
            int(round(gx0 + normalized.x1 * width)),
            int(round(gy0 + normalized.y1 * height)),
        )

    def _variation(self, character: str, role: str) -> tuple[float, int, int]:
        amount = max(0.0, min(1.0, self.options.natural_variation))
        if amount == 0:
            return 1.0, 0, 0
        digest = hashlib.blake2b(
            f"{self.options.random_seed}:{character}:{role}".encode("utf-8"), digest_size=8
        ).digest()
        values = [byte / 255.0 for byte in digest[:3]]
        scale = 1.0 + (values[0] - 0.5) * 0.04 * amount
        dx = int(round((values[1] - 0.5) * 8 * amount))
        dy = int(round((values[2] - 0.5) * 8 * amount))
        return scale, dx, dy

    def _remap_fallback(self, mask: np.ndarray, source_region, target_region, character: str, role: str) -> np.ndarray:
        canvas = self.options.canvas_size
        sx0, sy0, sx1, sy1 = source_region
        crop = mask[sy0:sy1, sx0:sx1]
        ys, xs = np.where(crop > 0)
        output = np.zeros((canvas, canvas), dtype=np.uint8)
        if len(xs) == 0:
            return output
        crop = crop[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
        tx0, ty0, tx1, ty1 = target_region
        target_width = max(1, tx1 - tx0)
        target_height = max(1, ty1 - ty0)
        pad = self.options.fallback_inner_padding
        available_width = max(1.0, target_width * (1.0 - 2.0 * pad))
        available_height = max(1.0, target_height * (1.0 - 2.0 * pad))
        height, width = crop.shape
        scale = min(available_width / width, available_height / height)
        variation_scale, dx, dy = self._variation(character, role)
        scale *= variation_scale
        new_width = max(1, int(round(width * scale)))
        new_height = max(1, int(round(height * scale)))
        resized = cv2.resize(
            crop,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
        )
        resized = (resized > 96).astype(np.uint8) * 255
        x = tx0 + (target_width - new_width) // 2 + dx
        y = ty0 + (target_height - new_height) // 2 + dy
        if role == "jongseong":
            y = ty1 - new_height - int(round(target_height * pad)) + dy
        x = max(0, min(canvas - new_width, x))
        y = max(0, min(canvas - new_height, y))
        output[y : y + new_height, x : x + new_width] = resized
        return output

    def compose(self, character: str) -> tuple[np.ndarray, list[np.ndarray], dict]:
        decomposition = decompose_syllable(character)
        roles = ["choseong", "jungseong"] + (["jongseong"] if decomposition.has_final else [])
        layers: list[np.ndarray] = []
        uses: list[ComponentUse] = []
        accumulated = np.zeros((self.options.canvas_size, self.options.canvas_size), dtype=np.uint8)
        for role in roles:
            requested = self._requested_form(decomposition, role)
            resolved, resolution = self.resolve_form(decomposition, role)
            record = self.library.records[resolved]
            source = self.library.masks[resolved]
            if resolution == "exact":
                layer = source.copy()
            else:
                layer = self._remap_fallback(
                    source,
                    record.source_region,
                    self._target_region(decomposition, role),
                    character,
                    role,
                )
            overlap = int(np.logical_and(accumulated > 0, layer > 0).sum())
            accumulated = np.maximum(accumulated, layer)
            layers.append(layer)
            uses.append(
                ComponentUse(
                    role=role,
                    requested_form=requested,
                    resolved_form=resolved,
                    resolution=resolution,
                    source_character=record.source_character,
                    template_candidates=record.candidate_count,
                    overlap_pixels=overlap,
                )
            )
        metadata = {
            "schema_version": "1.7.0",
            "character": character,
            "codepoint": f"U+{ord(character):04X}",
            "decomposition": asdict(decomposition),
            "resolution": {
                "exact_components": sum(use.resolution == "exact" for use in uses),
                "fallback_components": sum(use.resolution == "fallback" for use in uses),
            },
            "components": [use.to_dict() for use in uses],
            "composer_options": asdict(self.options),
        }
        return accumulated, layers, metadata
