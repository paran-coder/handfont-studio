from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees

import cv2
import numpy as np
from skimage.measure import find_contours

from .errors import VectorizationError
from .models import VectorizeOptions


@dataclass(frozen=True)
class VectorContour:
    index: int
    parent: int
    depth: int
    is_hole: bool
    area: float
    original_points: np.ndarray
    simplified_points: np.ndarray
    path_data: str
    path_commands: int


def _clean_polygon(points: np.ndarray) -> np.ndarray:
    polygon = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if len(polygon) > 1 and np.allclose(polygon[0], polygon[-1]):
        polygon = polygon[:-1]
    if len(polygon) < 3:
        raise VectorizationError("윤곽선 단순화 결과가 3개 점보다 적습니다.")
    keep = [0]
    for index in range(1, len(polygon)):
        if np.linalg.norm(polygon[index] - polygon[keep[-1]]) >= 0.20:
            keep.append(index)
    polygon = polygon[keep]
    if len(polygon) < 3:
        raise VectorizationError("중복 점 제거 후 윤곽선 점이 부족합니다.")
    return polygon


def _vertex_angle(prev: np.ndarray, current: np.ndarray, nxt: np.ndarray) -> float:
    a = prev - current
    b = nxt - current
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norm <= 1e-9:
        return 0.0
    cosine = float(np.clip(np.dot(a, b) / norm, -1.0, 1.0))
    return degrees(acos(cosine))


def _fmt(value: float, precision: int) -> str:
    text = f"{value:.{precision}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def polygon_to_quadratic_path(points: np.ndarray, options: VectorizeOptions) -> tuple[str, int]:
    polygon = _clean_polygon(points)
    count = len(polygon)
    entries = np.zeros_like(polygon)
    exits = np.zeros_like(polygon)
    smooth = np.zeros(count, dtype=bool)

    for index in range(count):
        prev = polygon[(index - 1) % count]
        current = polygon[index]
        nxt = polygon[(index + 1) % count]
        angle = _vertex_angle(prev, current, nxt)
        len_prev = float(np.linalg.norm(prev - current))
        len_next = float(np.linalg.norm(nxt - current))
        # Acute and orthogonal vertices stay sharp. Dense curved samples receive
        # short entry/exit handles around the source point.
        is_smooth = angle >= options.corner_angle_degrees and min(len_prev, len_next) >= 0.8
        smooth[index] = is_smooth
        if is_smooth and options.smoothing_radius > 0:
            radius = min(options.smoothing_radius, 0.45)
            entries[index] = current + (prev - current) * radius
            exits[index] = current + (nxt - current) * radius
        else:
            entries[index] = current
            exits[index] = current

    precision = options.coordinate_precision
    commands: list[str] = [f"M {_fmt(exits[-1, 0], precision)} {_fmt(exits[-1, 1], precision)}"]
    command_count = 1
    for index in range(count):
        entry = entries[index]
        current = polygon[index]
        exit_point = exits[index]
        commands.append(f"L {_fmt(entry[0], precision)} {_fmt(entry[1], precision)}")
        command_count += 1
        if smooth[index] and options.smoothing_radius > 0:
            commands.append(
                "Q "
                f"{_fmt(current[0], precision)} {_fmt(current[1], precision)} "
                f"{_fmt(exit_point[0], precision)} {_fmt(exit_point[1], precision)}"
            )
            command_count += 1
    commands.append("Z")
    return " ".join(commands), command_count


def _signed_area(points: np.ndarray) -> float:
    x = points[:, 0]
    y = points[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _interior_point(points: np.ndarray) -> tuple[float, float]:
    polygon = np.round(points).astype(np.int32)
    x, y, width, height = cv2.boundingRect(polygon.reshape(-1, 1, 2))
    local = polygon - np.array([x, y], dtype=np.int32)
    canvas = np.zeros((max(height + 3, 4), max(width + 3, 4)), dtype=np.uint8)
    cv2.fillPoly(canvas, [local.reshape(-1, 1, 2)], 255)
    distance = cv2.distanceTransform(canvas, cv2.DIST_L2, 3)
    _, _, _, max_location = cv2.minMaxLoc(distance)
    return float(x + max_location[0]), float(y + max_location[1])


def _resolve_hierarchy(polygons: list[np.ndarray], areas: list[float]) -> tuple[list[int], list[int]]:
    parents = [-1] * len(polygons)
    interior = [_interior_point(points) for points in polygons]
    for index, point in enumerate(interior):
        candidates: list[tuple[float, int]] = []
        for candidate_index, candidate in enumerate(polygons):
            if candidate_index == index or areas[candidate_index] <= areas[index]:
                continue
            test = cv2.pointPolygonTest(candidate.astype(np.float32).reshape(-1, 1, 2), point, False)
            if test > 0:
                candidates.append((areas[candidate_index], candidate_index))
        if candidates:
            parents[index] = min(candidates)[1]

    depths: list[int] = []
    for index in range(len(polygons)):
        depth = 0
        parent = parents[index]
        seen: set[int] = set()
        while parent >= 0 and parent not in seen:
            seen.add(parent)
            depth += 1
            parent = parents[parent]
        depths.append(depth)
    return parents, depths


def extract_vector_contours(mask: np.ndarray, options: VectorizeOptions) -> list[VectorContour]:
    # Marching squares at the 0.5 boundary traces pixel edges at sub-pixel
    # coordinates. This avoids the systematic one-pixel shrinkage produced by
    # centerline contours and materially improves SVG raster fidelity.
    padded = np.pad(mask > 0, 1, mode="constant", constant_values=False)
    raw = find_contours(
        padded,
        level=0.5,
        fully_connected="high",
        positive_orientation="high",
    )
    polygons: list[np.ndarray] = []
    areas: list[float] = []
    for contour in raw:
        points = np.stack([contour[:, 1] - 1.0, contour[:, 0] - 1.0], axis=1).astype(np.float32)
        area = abs(_signed_area(points))
        if area < options.minimum_component_area:
            continue
        polygons.append(points)
        areas.append(area)
    if not polygons:
        raise VectorizationError("최소 면적 기준을 통과한 윤곽선이 없습니다.")

    parents, depths = _resolve_hierarchy(polygons, areas)
    output: list[VectorContour] = []
    for index, points in enumerate(polygons):
        contour_cv = points.reshape(-1, 1, 2)
        perimeter = float(cv2.arcLength(contour_cv, True))
        epsilon = max(0.20, perimeter * options.simplify_tolerance)
        approximated = cv2.approxPolyDP(contour_cv, epsilon, True).reshape(-1, 2)
        if len(approximated) < 3:
            approximated = points
        path_data, command_count = polygon_to_quadratic_path(approximated, options)
        output.append(
            VectorContour(
                index=index,
                parent=parents[index],
                depth=depths[index],
                is_hole=bool(depths[index] % 2),
                area=areas[index],
                original_points=points,
                simplified_points=np.asarray(approximated, dtype=np.float64),
                path_data=path_data,
                path_commands=command_count,
            )
        )
    return output
