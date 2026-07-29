from __future__ import annotations

import json
import random
from pathlib import Path

import cv2
import numpy as np

from .field_validation import FieldOptions, preflight_capture_session
from .synthetic import render_written_page, synthesize_capture


def _add_glare(image: np.ndarray, strength: float, seed: int) -> np.ndarray:
    if strength <= 0:
        return image
    rng = random.Random(seed)
    result = image.copy()
    h, w = result.shape[:2]
    overlay = np.zeros_like(result)
    center = (rng.randint(int(w * 0.35), int(w * 0.65)), rng.randint(int(h * 0.3), int(h * 0.7)))
    axes = (max(15, int(w * strength)), max(18, int(h * strength * 0.65)))
    cv2.ellipse(overlay, center, axes, rng.uniform(-25, 25), 0, 360, (255, 255, 255), -1, cv2.LINE_AA)
    overlay = cv2.GaussianBlur(overlay, (0, 0), sigmaX=max(5, w * strength * 0.25))
    alpha = np.clip(overlay.astype(np.float32) / 255.0, 0, 0.82)
    return np.clip(result.astype(np.float32) * (1 - alpha) + 255 * alpha, 0, 255).astype(np.uint8)


def _degrade_resolution(image: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 0.99:
        return image
    h, w = image.shape[:2]
    small = cv2.resize(image, (max(320, int(w * scale)), max(420, int(h * scale))), interpolation=cv2.INTER_AREA)
    return small


def generate_field_benchmark(output_dir: Path | str, *, seed: int = 20260729, count_per_class: int = 18) -> dict:
    output = Path(output_dir)
    photos = output / "photos"
    photos.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    rng = random.Random(seed)
    page_image = render_written_page(1, dpi=150, seed=seed)

    scenarios = {
        "accept": dict(perspective=(0.018, 0.055), brightness=(-4, 5), blur=[1], noise=(0.5, 2.2), jpeg=(88, 97), shadow=(0.02, 0.08), glare=(0.0, 0.003), scale=(0.92, 1.0)),
        "review": dict(perspective=(0.07, 0.12), brightness=(-10, 9), blur=[1, 3], noise=(1.8, 4.0), jpeg=(74, 88), shadow=(0.11, 0.20), glare=(0.012, 0.026), scale=(0.76, 0.90)),
        "retake": dict(perspective=(0.10, 0.14), brightness=(-18, 14), blur=[3], noise=(2.8, 5.2), jpeg=(68, 82), shadow=(0.27, 0.40), glare=(0.065, 0.105), scale=(0.82, 0.94)),
        "blocked": dict(perspective=(0.08, 0.15), brightness=(-18, 12), blur=[3, 5], noise=(3.0, 6.0), jpeg=(60, 78), shadow=(0.18, 0.32), glare=(0.02, 0.05), scale=(0.58, 0.82)),
    }
    for label, params in scenarios.items():
        for index in range(count_per_class):
            local_seed = seed + len(records) * 101
            image, markers = synthesize_capture(
                page_image,
                seed=local_seed,
                perspective=rng.uniform(*params["perspective"]),
                brightness=rng.uniform(*params["brightness"]),
                contrast=rng.uniform(0.92, 1.10),
                blur=rng.choice(params["blur"]),
                noise=rng.uniform(*params["noise"]),
                jpeg_quality=rng.randint(*params["jpeg"]),
                shadow=rng.uniform(*params["shadow"]),
            )
            image = _add_glare(image, rng.uniform(*params["glare"]), local_seed)
            if label == "blocked":
                # Hide one registration marker so the expected outcome is a hard block.
                marker = markers[index % 4]
                scale_x = image.shape[1] / max(1, int(page_image.shape[1] * 1.24))
                scale_y = image.shape[0] / max(1, int(page_image.shape[0] * 1.18))
                center = (int(marker[0] * scale_x), int(marker[1] * scale_y))
                radius = max(24, int(min(image.shape[:2]) * 0.028))
                cv2.rectangle(image, (center[0]-radius, center[1]-radius), (center[0]+radius, center[1]+radius), (246,246,246), -1)
            image = _degrade_resolution(image, rng.uniform(*params["scale"]))
            name = f"{label}-{index + 1:02d}.jpg"
            cv2.imwrite(str(photos / name), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
            records.append({"file": name, "expected": label})

    truth_path = output / "ground-truth.json"
    truth_path.write_text(json.dumps({"schema_version": "1.9.0", "seed": seed, "records": records}, indent=2), encoding="utf-8")
    report = preflight_capture_session(
        [photos], output / "processed", FieldOptions(expected_pages=(1,), data_origin="synthetic")
    )
    predicted = {Path(item["input_path"]).name: item["status"] for item in report["photos"]}
    matrix = {expected: {actual: 0 for actual in ("accept", "review", "retake", "blocked")} for expected in scenarios}
    correct = 0
    for record in records:
        actual = predicted.get(record["file"], "blocked")
        matrix[record["expected"]][actual] += 1
        correct += int(actual == record["expected"])
    summary = {
        "schema_version": "1.9.0",
        "data_origin": "synthetic",
        "count": len(records),
        "correct": correct,
        "accuracy": round(correct / max(1, len(records)), 6),
        "confusion_matrix": matrix,
        "truth_note": "합성 조건 라벨과 규칙 기반 판정의 일치율이며 실제 사용자 촬영 정확도가 아닙니다.",
    }
    (output / "benchmark-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
