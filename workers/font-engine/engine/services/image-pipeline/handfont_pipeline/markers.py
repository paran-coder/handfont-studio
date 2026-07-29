from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .errors import MarkerDetectionError
from .models import MarkerResult


@dataclass(frozen=True)
class _Candidate:
    center: tuple[float, float]
    area: float
    fill_ratio: float
    aspect: float
    darkness: float
    bbox: tuple[int, int, int, int]


def _threshold_variants(gray: np.ndarray) -> list[np.ndarray]:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    variants: list[np.ndarray] = []
    for threshold in (70, 100, 130, 160, 190):
        _, mask = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY_INV)
        variants.append(mask)
    variants.append(
        cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            81,
            12,
        )
    )
    return variants


def _deduplicate(candidates: list[_Candidate], radius: float) -> list[_Candidate]:
    result: list[_Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.area * item.fill_ratio, reverse=True):
        if all(np.hypot(candidate.center[0] - existing.center[0], candidate.center[1] - existing.center[1]) > radius for existing in result):
            result.append(candidate)
    return result


def _collect_candidates(gray: np.ndarray) -> list[_Candidate]:
    height, width = gray.shape
    image_area = float(height * width)
    minimum_area = image_area * 0.000025
    maximum_area = image_area * 0.006
    candidates: list[_Candidate] = []

    for mask in _threshold_variants(gray):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if not minimum_area <= area <= maximum_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            if min(w, h) < 8:
                continue
            aspect = w / float(h)
            if not 0.58 <= aspect <= 1.72:
                continue
            rectangle_area = float(w * h)
            fill_ratio = area / rectangle_area if rectangle_area else 0.0
            if fill_ratio < 0.55:
                continue
            patch = gray[y : y + h, x : x + w]
            darkness = 1.0 - float(np.mean(patch)) / 255.0
            if darkness < 0.45:
                continue
            perimeter = cv2.arcLength(contour, True)
            approximation = cv2.approxPolyDP(contour, 0.08 * perimeter, True)
            if len(approximation) < 4 or len(approximation) > 8:
                continue
            moments = cv2.moments(contour)
            if moments["m00"]:
                cx = moments["m10"] / moments["m00"]
                cy = moments["m01"] / moments["m00"]
            else:
                cx, cy = x + w / 2.0, y + h / 2.0
            candidates.append(
                _Candidate(
                    center=(float(cx), float(cy)),
                    area=area,
                    fill_ratio=fill_ratio,
                    aspect=aspect,
                    darkness=darkness,
                    bbox=(x, y, w, h),
                )
            )

    return _deduplicate(candidates, radius=max(width, height) * 0.012)


def _corner_score(candidate: _Candidate, corner: tuple[float, float], diagonal: float, image_area: float) -> float:
    distance = np.hypot(candidate.center[0] - corner[0], candidate.center[1] - corner[1]) / diagonal
    squareness = 1.0 - min(abs(np.log(max(candidate.aspect, 1e-6))), 1.0)
    area_score = min(candidate.area / (image_area * 0.0006), 1.0)
    return (
        0.34 * candidate.fill_ratio
        + 0.22 * candidate.darkness
        + 0.18 * squareness
        + 0.12 * area_score
        + 0.14 * max(0.0, 1.0 - distance * 3.0)
    )


def order_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).ravel()
    ordered = np.empty((4, 2), dtype=np.float32)
    ordered[0] = points[np.argmin(sums)]  # top-left
    ordered[2] = points[np.argmax(sums)]  # bottom-right
    ordered[1] = points[np.argmin(differences)]  # top-right
    ordered[3] = points[np.argmax(differences)]  # bottom-left
    return ordered


def detect_markers(image: np.ndarray) -> MarkerResult:
    if image.ndim != 3 or image.shape[2] != 3:
        raise MarkerDetectionError("등록 마커 검출에는 BGR 컬러 이미지가 필요합니다.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    diagonal = float(np.hypot(width, height))
    image_area = float(width * height)
    candidates = _collect_candidates(gray)
    if len(candidates) < 4:
        raise MarkerDetectionError(f"등록 마커 후보가 부족합니다: {len(candidates)}개")

    corners = [
        (0.0, 0.0),
        (float(width - 1), 0.0),
        (float(width - 1), float(height - 1)),
        (0.0, float(height - 1)),
    ]
    selected: list[_Candidate] = []
    scores: list[float] = []
    for index, corner in enumerate(corners):
        def in_corner_band(item: _Candidate) -> bool:
            x, y = item.center
            if index == 0:
                return x < width * 0.38 and y < height * 0.30
            if index == 1:
                return x > width * 0.62 and y < height * 0.30
            if index == 2:
                return x > width * 0.62 and y > height * 0.70
            return x < width * 0.38 and y > height * 0.70

        pool = [item for item in candidates if in_corner_band(item)]
        if not pool:
            raise MarkerDetectionError(f"{index + 1}번 모서리의 등록 마커를 찾지 못했습니다.")
        ranked = sorted(
            ((item, _corner_score(item, corner, diagonal, image_area)) for item in pool),
            key=lambda pair: pair[1],
            reverse=True,
        )
        selected.append(ranked[0][0])
        scores.append(float(ranked[0][1]))

    selected_areas = np.array([item.area for item in selected], dtype=np.float32)
    median_area = float(np.median(selected_areas))
    if median_area <= 0 or float(np.min(selected_areas)) < median_area * 0.45 or float(np.max(selected_areas)) > median_area * 2.2:
        raise MarkerDetectionError("등록 마커 후보의 크기가 서로 일치하지 않습니다.")
    if min(item.fill_ratio for item in selected) < 0.68 or min(item.darkness for item in selected) < 0.56:
        raise MarkerDetectionError("등록 마커 후보 중 채움 또는 명암 기준을 만족하지 않는 항목이 있습니다.")

    points = order_points(np.array([item.center for item in selected], dtype=np.float32))
    polygon_area = abs(float(cv2.contourArea(points.reshape(-1, 1, 2))))
    if polygon_area < image_area * 0.36:
        raise MarkerDetectionError("검출된 등록 마커 사각형이 페이지 영역보다 지나치게 작습니다.")

    top = np.linalg.norm(points[1] - points[0])
    bottom = np.linalg.norm(points[2] - points[3])
    left = np.linalg.norm(points[3] - points[0])
    right = np.linalg.norm(points[2] - points[1])
    if min(top, bottom, left, right) < min(width, height) * 0.45:
        raise MarkerDetectionError("등록 마커 사이의 거리가 비정상적입니다.")

    diagnostics = [
        {
            "center": [round(item.center[0], 3), round(item.center[1], 3)],
            "bbox": list(item.bbox),
            "area": round(item.area, 3),
            "fill_ratio": round(item.fill_ratio, 4),
            "aspect": round(item.aspect, 4),
            "darkness": round(item.darkness, 4),
        }
        for item in selected
    ]
    return MarkerResult(points=points, candidates=diagnostics, confidence=float(np.mean(scores)))
