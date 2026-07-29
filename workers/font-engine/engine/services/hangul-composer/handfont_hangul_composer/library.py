from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .models import TemplateRecord


@dataclass
class _Candidate:
    form_id: str
    role: str
    jamo: str
    source_character: str
    source_codepoint: str
    region: tuple[int, int, int, int]
    mask: np.ndarray


def _normalize_mask(mask: np.ndarray, canvas: int = 256, body: int = 220) -> np.ndarray:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return np.zeros((canvas, canvas), dtype=np.uint8)
    crop = mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    height, width = crop.shape
    scale = min(body / max(width, 1), body / max(height, 1))
    new_width = max(1, int(round(width * scale)))
    new_height = max(1, int(round(height * scale)))
    resized = cv2.resize(
        crop,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC,
    )
    resized = (resized > 96).astype(np.uint8)
    output = np.zeros((canvas, canvas), dtype=np.uint8)
    x = (canvas - new_width) // 2
    y = (canvas - new_height) // 2
    output[y : y + new_height, x : x + new_width] = resized
    return output


def _pair_iou(left: np.ndarray, right: np.ndarray) -> float:
    a = left > 0
    b = right > 0
    union = int(np.logical_or(a, b).sum())
    if not union:
        return 1.0
    return float(np.logical_and(a, b).sum()) / union


def _select_medoid(candidates: list[_Candidate]) -> _Candidate:
    if len(candidates) == 1:
        return candidates[0]
    normalized = [_normalize_mask(item.mask) for item in candidates]
    scores: list[float] = []
    for index, mask in enumerate(normalized):
        similarities = [_pair_iou(mask, other) for j, other in enumerate(normalized) if j != index]
        scores.append(float(np.mean(similarities)))
    best_index = max(range(len(candidates)), key=lambda index: (scores[index], -ord(candidates[index].source_character)))
    return candidates[best_index]


def _parse_form(form_id: str) -> tuple[str, str | None]:
    parts = form_id.split(":")
    layout = parts[2]
    state = parts[3] if len(parts) > 3 else None
    return layout, state


class TemplateLibrary:
    def __init__(self, records: dict[str, TemplateRecord], masks: dict[str, np.ndarray], root: Path):
        self.records = records
        self.masks = masks
        self.root = root

    @classmethod
    def build(cls, position_map_path: Path, masks_dir: Path, output_dir: Path) -> "TemplateLibrary":
        output_dir.mkdir(parents=True, exist_ok=True)
        template_dir = output_dir / "templates"
        template_dir.mkdir(exist_ok=True)
        data = json.loads(position_map_path.read_text(encoding="utf-8"))
        candidates: dict[str, list[_Candidate]] = {}
        for entry in data["entries"]:
            source_path = masks_dir / f"U+{ord(entry['character']):04X}.png"
            source = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
            if source is None:
                raise FileNotFoundError(source_path)
            for component in entry["components"]:
                x0, y0, x1, y1 = map(int, component["pixel_region"])
                cropped = np.zeros_like(source)
                cropped[y0:y1, x0:x1] = source[y0:y1, x0:x1]
                candidate = _Candidate(
                    form_id=component["form_id"],
                    role=component["role"],
                    jamo=component["jamo"],
                    source_character=entry["character"],
                    source_codepoint=entry["codepoint"],
                    region=(x0, y0, x1, y1),
                    mask=cropped,
                )
                candidates.setdefault(candidate.form_id, []).append(candidate)

        records: dict[str, TemplateRecord] = {}
        masks: dict[str, np.ndarray] = {}
        manifest_entries = []
        for form_id in sorted(candidates):
            pool = candidates[form_id]
            selected = _select_medoid(pool)
            safe_name = form_id.replace(":", "_")
            path = template_dir / f"{safe_name}.png"
            if not cv2.imwrite(str(path), selected.mask):
                raise OSError(f"템플릿 마스크를 저장하지 못했습니다: {path}")
            layout, state = _parse_form(form_id)
            record = TemplateRecord(
                form_id=form_id,
                role=selected.role,
                jamo=selected.jamo,
                source_character=selected.source_character,
                source_codepoint=selected.source_codepoint,
                source_region=selected.region,
                candidate_count=len(pool),
                selection_method="normalized-mask-medoid-v1",
                mask_path=path,
                exact_layout=layout,
                exact_state=state,
            )
            records[form_id] = record
            masks[form_id] = selected.mask
            manifest_entries.append(record.to_dict(output_dir))

        manifest = {
            "schema_version": "1.7.0",
            "selection_method": "normalized-mask-medoid-v1",
            "form_count": len(records),
            "singleton_forms": sum(record.candidate_count == 1 for record in records.values()),
            "multi_candidate_forms": sum(record.candidate_count > 1 for record in records.values()),
            "templates": manifest_entries,
        }
        (output_dir / "template-library.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return cls(records, masks, output_dir)

    @classmethod
    def load(cls, manifest_path: Path) -> "TemplateLibrary":
        root = manifest_path.parent
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        records: dict[str, TemplateRecord] = {}
        masks: dict[str, np.ndarray] = {}
        for item in data["templates"]:
            path = root / item["mask_path"]
            record = TemplateRecord(
                form_id=item["form_id"],
                role=item["role"],
                jamo=item["jamo"],
                source_character=item["source_character"],
                source_codepoint=item["source_codepoint"],
                source_region=tuple(item["source_region"]),
                candidate_count=int(item["candidate_count"]),
                selection_method=item["selection_method"],
                mask_path=path,
                exact_layout=item["exact_layout"],
                exact_state=item.get("exact_state"),
            )
            mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise FileNotFoundError(path)
            records[record.form_id] = record
            masks[record.form_id] = mask
        return cls(records, masks, root)
