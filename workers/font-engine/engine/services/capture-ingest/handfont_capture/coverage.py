from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


USABLE = {"ok", "too_dense"}
REVIEW = {"too_dense"}


def analyze_position_coverage(page_metadata: list[dict[str, Any]], position_map_path: Path | str) -> dict[str, Any]:
    status_by_character: dict[str, str] = {}
    cell_by_character: dict[str, str] = {}
    quality_by_cell: dict[str, dict[str, Any]] = {}
    for metadata in page_metadata:
        for cell in metadata.get("cells", []):
            character = cell.get("character") or ""
            if not character:
                continue
            status_by_character[character] = cell.get("quality", {}).get("status", "missing")
            cell_by_character[character] = cell.get("cell_id", "")
            quality_by_cell[cell.get("cell_id", "")] = cell.get("quality", {})

    position_map = json.loads(Path(position_map_path).read_text(encoding="utf-8"))
    providers: dict[str, list[dict[str, str]]] = defaultdict(list)
    entry_forms: dict[str, list[str]] = {}
    for entry in position_map["entries"]:
        character = entry["character"]
        forms = [component["form_id"] for component in entry.get("components", [])]
        entry_forms[character] = forms
        status = status_by_character.get(character, "missing")
        for form in forms:
            providers[form].append({
                "character": character,
                "cell_id": cell_by_character.get(character, ""),
                "status": status,
            })

    covered: list[str] = []
    review: list[str] = []
    missing: list[str] = []
    form_details: list[dict[str, Any]] = []
    for form in sorted(providers):
        items = providers[form]
        usable = [item for item in items if item["status"] in USABLE]
        clean = [item for item in usable if item["status"] not in REVIEW]
        if clean:
            state = "covered"
            covered.append(form)
        elif usable:
            state = "review"
            review.append(form)
        else:
            state = "missing"
            missing.append(form)
        form_details.append({"form_id": form, "state": state, "providers": items})

    rewrite_candidates: list[dict[str, Any]] = []
    for character, forms in entry_forms.items():
        status = status_by_character.get(character, "missing")
        missing_forms = [form for form in forms if form in missing]
        review_forms = [form for form in forms if form in review]
        if status not in USABLE or missing_forms or review_forms:
            cell_id = cell_by_character.get(character, "")
            quality = quality_by_cell.get(cell_id, {})
            priority = len(missing_forms) * 10 + len(review_forms) * 3
            if status == "missing":
                priority += 12
            elif status == "too_sparse":
                priority += 9
            elif status == "too_dense":
                priority += 4
            rewrite_candidates.append({
                "character": character,
                "cell_id": cell_id,
                "status": status,
                "priority": priority,
                "missing_forms": missing_forms,
                "review_forms": review_forms,
                "foreground_ratio": quality.get("foreground_ratio"),
            })
    rewrite_candidates.sort(key=lambda item: (-item["priority"], item["cell_id"]))

    total = len(providers)
    return {
        "schema_version": "1.8.0",
        "expected_position_forms": total,
        "covered_position_forms": len(covered),
        "review_position_forms": len(review),
        "missing_position_forms": len(missing),
        "coverage_ratio": round((len(covered) + len(review)) / max(total, 1), 6),
        "clean_coverage_ratio": round(len(covered) / max(total, 1), 6),
        "covered_forms": covered,
        "review_forms": review,
        "missing_forms": missing,
        "forms": form_details,
        "rewrite_candidates": rewrite_candidates,
    }
