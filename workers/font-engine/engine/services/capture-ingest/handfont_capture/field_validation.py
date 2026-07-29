from __future__ import annotations

import csv
import html
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np

from .compat import IMAGE_PIPELINE_ROOT  # noqa: F401
from .identifier import PageIdentifier
from .manual import load_manual_corners, validate_manual_corners
from .quality import capture_quality
from .session import SUPPORTED_EXTENSIONS, _input_files, _manual_for
from handfont_pipeline.config import DEFAULT_BLANK_DIR, DEFAULT_LAYOUT_PATH, load_layout
from handfont_pipeline.io import read_input
from handfont_pipeline.markers import detect_markers
from handfont_pipeline.perspective import rectify_page


STATUS_ORDER = {"accept": 0, "review": 1, "retake": 2, "blocked": 3}
STATUS_LABEL_KO = {
    "accept": "통과",
    "review": "검수 필요",
    "retake": "재촬영 권장",
    "blocked": "처리 불가",
}

ACTION_TEXT = {
    "low-resolution": "카메라 원본 해상도로 다시 촬영하고 메신저 저화질 전송을 피하십시오.",
    "blur": "휴대전화를 고정하고 화면을 눌러 초점을 맞춘 뒤 다시 촬영하십시오.",
    "exposure": "종이가 회색이나 새하얗게 날아가지 않도록 균일한 밝기에서 다시 촬영하십시오.",
    "glare": "조명이나 창문 반사가 종이에 비치지 않도록 촬영 각도를 바꾸십시오.",
    "shadow": "손·휴대전화 그림자를 제거하고 양쪽에서 균일하게 빛을 비추십시오.",
    "perspective": "카메라를 종이 중앙 위에 두고 종이와 평행하게 다시 촬영하십시오.",
    "page-coverage": "종이 전체와 네 모서리가 화면 대부분을 차지하도록 가까이 촬영하십시오.",
    "manual-corners": "수동 모서리로 복구되었습니다. 등록 마커가 모두 보이는 사진을 권장합니다.",
    "marker-low-confidence": "등록 마커를 가리지 말고 종이 네 모서리를 선명하게 촬영하십시오.",
    "page-id-low-confidence": "페이지 코드와 안내 문자가 흐리지 않게 다시 촬영하십시오.",
    "marker-failed": "등록 마커 네 개가 모두 보이는 사진이 필요합니다.",
    "page-id-failed": "페이지 번호를 구분할 수 없습니다. 전체 페이지를 선명하게 다시 촬영하십시오.",
    "missing-page": "해당 페이지를 촬영해 추가하십시오.",
}


@dataclass(frozen=True)
class FieldThresholds:
    min_megapixels_accept: float = 2.0
    min_megapixels_retake: float = 1.15
    sharpness_accept: float = 0.25
    sharpness_retake: float = 0.13
    exposure_accept: float = 0.68
    exposure_retake: float = 0.46
    glare_accept: float = 0.050
    glare_retake: float = 0.085
    shadow_accept: float = 0.14
    shadow_retake: float = 0.29
    perspective_accept: float = 0.15
    perspective_retake: float = 0.30
    coverage_accept: float = 0.52
    coverage_retake: float = 0.38
    marker_confidence_accept: float = 0.70
    page_confidence_accept: float = 0.48
    page_confidence_block: float = 0.30


@dataclass(frozen=True)
class FieldOptions:
    dpi: int = 150
    expected_pages: tuple[int, ...] = tuple(range(1, 10))
    data_origin: str = "synthetic"
    profile: str = "balanced"
    thresholds: FieldThresholds = FieldThresholds()


@dataclass
class PhotoAssessment:
    input_path: Path
    width: int
    height: int
    megapixels: float
    page: int | None
    status: str
    score: float
    reasons: list[str]
    actions: list[str]
    marker_method: str | None = None
    marker_confidence: float = 0.0
    page_confidence: float = 0.0
    sharpness: float = 0.0
    exposure: float = 0.0
    glare: float = 0.0
    shadow: float = 0.0
    perspective: float = 0.0
    page_coverage: float = 0.0
    highlight_clip: float = 0.0
    dark_clip: float = 0.0
    marker_points: list[list[float]] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["input_path"] = str(self.input_path)
        for key in (
            "megapixels", "score", "marker_confidence", "page_confidence", "sharpness",
            "exposure", "glare", "shadow", "perspective", "page_coverage",
            "highlight_clip", "dark_clip",
        ):
            payload[key] = round(float(payload[key]), 6)
        return payload


def _perspective_metrics(points: np.ndarray, width: int, height: int) -> tuple[float, float]:
    points = np.asarray(points, dtype=np.float32)
    area = abs(float(cv2.contourArea(points.reshape(-1, 1, 2))))
    coverage = area / max(1.0, float(width * height))
    top = float(np.linalg.norm(points[1] - points[0]))
    right = float(np.linalg.norm(points[2] - points[1]))
    bottom = float(np.linalg.norm(points[2] - points[3]))
    left = float(np.linalg.norm(points[3] - points[0]))
    horizontal_imbalance = abs(top - bottom) / max(top, bottom, 1.0)
    vertical_imbalance = abs(left - right) / max(left, right, 1.0)
    angle_deviations: list[float] = []
    for index in range(4):
        previous = points[(index - 1) % 4] - points[index]
        following = points[(index + 1) % 4] - points[index]
        denominator = max(float(np.linalg.norm(previous) * np.linalg.norm(following)), 1e-6)
        cosine = float(np.clip(np.dot(previous, following) / denominator, -1.0, 1.0))
        angle = float(np.degrees(np.arccos(cosine)))
        angle_deviations.append(abs(angle - 90.0) / 90.0)
    severity = 0.34 * horizontal_imbalance + 0.34 * vertical_imbalance + 0.32 * max(angle_deviations)
    return float(np.clip(severity, 0.0, 1.0)), float(np.clip(coverage, 0.0, 1.0))


def _illumination_metrics(rectified: np.ndarray) -> tuple[float, float, float, float, float]:
    gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
    gray_float = gray.astype(np.float32)
    height, width = gray.shape
    long_side = max(gray.shape)

    # Exposure is evaluated from the paper tone and usable ink contrast rather
    # than from the number of white pixels, because a clean sheet is naturally bright.
    p05, p50, p92 = np.percentile(gray, [5, 50, 92])
    paper_score = float(np.clip(1.0 - abs(float(p92) - 244.0) / 72.0, 0.0, 1.0))
    contrast_score = float(np.clip((float(p92) - float(p05)) / 62.0, 0.0, 1.0))
    highlight_clip = float(np.mean(gray >= 254))
    dark_clip = float(np.mean(gray <= 5))
    clipping_penalty = min(1.0, dark_clip * 18.0 + max(0.0, highlight_clip - 0.72) * 2.8)
    exposure = float(np.clip(0.62 * paper_score + 0.38 * contrast_score - 0.42 * clipping_penalty, 0.0, 1.0))

    # Local positive luminance anomalies are treated as glare. A morphological
    # opening removes text/grid edges and keeps only broad reflected-light patches.
    local_kernel = max(41, int(round(long_side / 18)) | 1)
    local_background = cv2.GaussianBlur(gray_float, (local_kernel, local_kernel), 0)
    residual = gray_float - local_background
    glare_mask = ((gray > 250) & (residual > 18.0)).astype(np.uint8) * 255
    open_size = max(5, int(round(long_side / 180)) | 1)
    glare_mask = cv2.morphologyEx(glare_mask, cv2.MORPH_OPEN, np.ones((open_size, open_size), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(glare_mask, 8)
    minimum_area = gray.size * 0.00018
    glare_area = sum(int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count) if stats[index, cv2.CC_STAT_AREA] >= minimum_area)
    glare = float(glare_area / max(1, gray.size))

    # Shadow is the robust spread of a heavily blurred paper illumination field.
    broad_kernel = max(81, int(round(long_side / 7)) | 1)
    broad = cv2.GaussianBlur(gray_float, (broad_kernel, broad_kernel), 0)
    margin_y, margin_x = int(height * 0.06), int(width * 0.06)
    central = broad[margin_y:height - margin_y, margin_x:width - margin_x]
    valid = central[central > 150]
    if valid.size:
        p10, p90 = np.percentile(valid, [10, 90])
        shadow = float(np.clip((p90 - p10) / 120.0, 0.0, 1.0))
    else:
        shadow = 1.0
    return exposure, glare, shadow, highlight_clip, dark_clip


def _severity_reason(
    value: float,
    accept: float,
    retake: float,
    *,
    lower_is_bad: bool,
    code: str,
) -> tuple[str | None, int]:
    if lower_is_bad:
        if value < retake:
            return code, 2
        if value < accept:
            return code, 1
    else:
        if value > retake:
            return code, 2
        if value > accept:
            return code, 1
    return None, 0


def _classify(
    *,
    thresholds: FieldThresholds,
    megapixels: float,
    marker_method: str,
    marker_confidence: float,
    page_confidence: float,
    sharpness: float,
    exposure: float,
    glare: float,
    shadow: float,
    perspective: float,
    page_coverage: float,
) -> tuple[str, float, list[str], list[str]]:
    reasons: list[str] = []
    severities: list[int] = []
    checks = [
        _severity_reason(megapixels, thresholds.min_megapixels_accept, thresholds.min_megapixels_retake, lower_is_bad=True, code="low-resolution"),
        _severity_reason(sharpness, thresholds.sharpness_accept, thresholds.sharpness_retake, lower_is_bad=True, code="blur"),
        _severity_reason(exposure, thresholds.exposure_accept, thresholds.exposure_retake, lower_is_bad=True, code="exposure"),
        _severity_reason(glare, thresholds.glare_accept, thresholds.glare_retake, lower_is_bad=False, code="glare"),
        _severity_reason(shadow, thresholds.shadow_accept, thresholds.shadow_retake, lower_is_bad=False, code="shadow"),
        _severity_reason(perspective, thresholds.perspective_accept, thresholds.perspective_retake, lower_is_bad=False, code="perspective"),
        _severity_reason(page_coverage, thresholds.coverage_accept, thresholds.coverage_retake, lower_is_bad=True, code="page-coverage"),
    ]
    for reason, severity in checks:
        if reason:
            reasons.append(reason)
            severities.append(severity)
    if marker_method == "manual":
        reasons.append("manual-corners")
        severities.append(1)
    elif marker_confidence < thresholds.marker_confidence_accept:
        reasons.append("marker-low-confidence")
        severities.append(1)
    if page_confidence < thresholds.page_confidence_accept:
        reasons.append("page-id-low-confidence")
        severities.append(1)

    maximum = max(severities, default=0)
    status = "retake" if maximum >= 2 else "review" if maximum == 1 else "accept"
    components = [
        min(1.0, megapixels / thresholds.min_megapixels_accept),
        sharpness,
        exposure,
        max(0.0, 1.0 - glare / max(thresholds.glare_retake, 1e-6)),
        max(0.0, 1.0 - shadow / max(thresholds.shadow_retake, 1e-6)),
        max(0.0, 1.0 - perspective / max(thresholds.perspective_retake, 1e-6)),
        min(1.0, page_coverage / thresholds.coverage_accept),
        marker_confidence if marker_method == "automatic" else 0.75,
        page_confidence,
    ]
    weights = np.array([0.08, 0.18, 0.10, 0.12, 0.12, 0.12, 0.08, 0.08, 0.12], dtype=np.float32)
    score = float(np.dot(np.array(components, dtype=np.float32), weights) * 100.0)
    actions = list(dict.fromkeys(ACTION_TEXT[reason] for reason in reasons if reason in ACTION_TEXT))
    return status, score, reasons, actions


def assess_photo(
    path: Path,
    *,
    identifier: PageIdentifier,
    layout: dict[str, Any],
    options: FieldOptions,
    manual: dict[str, np.ndarray],
) -> tuple[PhotoAssessment, np.ndarray | None]:
    image = read_input(path, render_dpi=options.dpi)
    height, width = image.shape[:2]
    megapixels = width * height / 1_000_000.0
    marker_method = "automatic"
    try:
        marker = detect_markers(image)
        points = marker.points
        marker_confidence = marker.confidence
    except Exception as automatic_error:
        manual_points = _manual_for(path, manual)
        if manual_points is None:
            return PhotoAssessment(
                input_path=path, width=width, height=height, megapixels=megapixels,
                page=None, status="blocked", score=0.0, reasons=["marker-failed"],
                actions=[ACTION_TEXT["marker-failed"]], error=str(automatic_error),
            ), image
        points = validate_manual_corners(manual_points, width, height)
        marker_method = "manual"
        marker_confidence = 1.0

    rectified, _ = rectify_page(image, points, layout, options.dpi)
    identification = identifier.identify(rectified)
    if identification.confidence < options.thresholds.page_confidence_block:
        return PhotoAssessment(
            input_path=path, width=width, height=height, megapixels=megapixels,
            page=identification.page, status="blocked", score=0.0,
            reasons=["page-id-failed"], actions=[ACTION_TEXT["page-id-failed"]],
            marker_method=marker_method, marker_confidence=marker_confidence,
            page_confidence=identification.confidence,
            marker_points=points.round(3).tolist(),
            error=f"page confidence {identification.confidence:.3f}",
        ), image

    sharpness, _, _, _ = capture_quality(
        image, marker_confidence, identification.confidence, marker_method
    )
    exposure, glare, shadow, highlight_clip, dark_clip = _illumination_metrics(rectified)
    perspective, coverage = _perspective_metrics(points, width, height)
    status, score, reasons, actions = _classify(
        thresholds=options.thresholds,
        megapixels=megapixels,
        marker_method=marker_method,
        marker_confidence=marker_confidence,
        page_confidence=identification.confidence,
        sharpness=sharpness,
        exposure=exposure,
        glare=glare,
        shadow=shadow,
        perspective=perspective,
        page_coverage=coverage,
    )
    return PhotoAssessment(
        input_path=path, width=width, height=height, megapixels=megapixels,
        page=identification.page, status=status, score=score, reasons=reasons,
        actions=actions, marker_method=marker_method, marker_confidence=marker_confidence,
        page_confidence=identification.confidence, sharpness=sharpness,
        exposure=exposure, glare=glare, shadow=shadow, perspective=perspective,
        page_coverage=coverage, highlight_clip=highlight_clip, dark_clip=dark_clip,
        marker_points=points.round(3).tolist(),
    ), image


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _build_overview(results: list[PhotoAssessment], output: Path) -> Path | None:
    if not results:
        return None
    tile_w, tile_h = 310, 390
    cols = 3
    rows = (len(results) + cols - 1) // cols
    canvas = np.full((rows * tile_h, cols * tile_w, 3), 248, dtype=np.uint8)
    border_colors = {
        "accept": (65, 140, 65), "review": (40, 150, 215),
        "retake": (55, 80, 220), "blocked": (35, 35, 35),
    }
    for index, result in enumerate(results):
        image = cv2.imread(str(result.input_path), cv2.IMREAD_COLOR)
        x = (index % cols) * tile_w + 20
        y = (index // cols) * tile_h + 15
        if image is not None:
            image = cv2.resize(image, (270, 285), interpolation=cv2.INTER_AREA)
            canvas[y:y + 285, x:x + 270] = image
        color = border_colors[result.status]
        cv2.rectangle(canvas, (x - 3, y - 3), (x + 273, y + 288), color, 4)
        page_text = f"P{result.page:02d}" if result.page else "P??"
        cv2.putText(canvas, f"{page_text} {result.status.upper()} {result.score:.1f}", (x, y + 312), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (20, 20, 20), 1, cv2.LINE_AA)
        reason = ",".join(result.reasons[:3]) or "ok"
        cv2.putText(canvas, reason[:42], (x, y + 337), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (45, 45, 45), 1, cv2.LINE_AA)
        cv2.putText(canvas, result.input_path.name[:38], (x, y + 361), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (65, 65, 65), 1, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), canvas)
    return output


def _build_html(report: dict[str, Any], output: Path) -> Path:
    rows: list[str] = []
    for item in report["photos"]:
        reasons = ", ".join(item["reasons"]) or "없음"
        actions = "<br>".join(html.escape(action) for action in item["actions"]) or "-"
        rows.append(
            "<tr>"
            f"<td>{html.escape(Path(item['input_path']).name)}</td>"
            f"<td>{item['page'] if item['page'] is not None else '-'}</td>"
            f"<td><span class='badge {item['status']}'>{STATUS_LABEL_KO[item['status']]}</span></td>"
            f"<td>{item['score']:.1f}</td><td>{item['sharpness']:.3f}</td>"
            f"<td>{item['glare']:.3f}</td><td>{item['shadow']:.3f}</td>"
            f"<td>{item['perspective']:.3f}</td><td>{item['page_coverage']:.3f}</td>"
            f"<td>{html.escape(reasons)}</td><td>{actions}</td></tr>"
        )
    css = """
    body{font-family:system-ui,-apple-system,'Noto Sans KR',sans-serif;margin:32px;color:#202124;background:#f6f7f9}
    main{max-width:1500px;margin:auto;background:#fff;padding:28px;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.08)}
    h1{margin-top:0}.summary{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.card{padding:12px 16px;border:1px solid #ddd;border-radius:10px;min-width:130px}
    table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid #e6e6e6;padding:9px;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#fafafa}
    .badge{padding:4px 8px;border-radius:999px;font-weight:700;white-space:nowrap}.accept{background:#e6f4ea;color:#176b2c}.review{background:#fff4db;color:#8a5700}.retake{background:#fde7e7;color:#a32323}.blocked{background:#e8eaed;color:#202124}
    .note{padding:12px;background:#f1f3f4;border-radius:10px;margin:14px 0}.scroll{overflow:auto}
    """
    counts = report["status_counts"]
    cards = "".join(f"<div class='card'><strong>{STATUS_LABEL_KO[key]}</strong><br>{counts.get(key,0)}장</div>" for key in STATUS_ORDER)
    body = f"""<!doctype html><html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>HandFont Field Validation</title><style>{css}</style></head><body><main>
    <h1>HandFont Studio 현장 촬영 검증</h1>
    <div class='note'>데이터 출처: <strong>{html.escape(report['data_origin'])}</strong> · 세션 판정: <strong>{STATUS_LABEL_KO[report['session_status']]}</strong> · 생성 시각: {html.escape(report['processed_at'])}</div>
    <div class='summary'>{cards}</div>
    <p>선택 페이지: {', '.join(map(str, report['selected_pages'])) or '-'} · 누락 페이지: {', '.join(map(str, report['missing_pages'])) or '없음'}</p>
    <div class='scroll'><table><thead><tr><th>파일</th><th>페이지</th><th>상태</th><th>점수</th><th>선명도</th><th>반사</th><th>그림자</th><th>원근</th><th>점유율</th><th>사유</th><th>조치</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
    </main></body></html>"""
    output.write_text(body, encoding="utf-8")
    return output


def preflight_capture_session(
    input_paths: Iterable[Path | str],
    output_dir: Path | str,
    options: FieldOptions = FieldOptions(),
    *,
    manual_corners_path: Path | str | None = None,
    layout_path: Path | str = DEFAULT_LAYOUT_PATH,
    blank_dir: Path | str = DEFAULT_BLANK_DIR,
) -> dict[str, Any]:
    if options.data_origin not in {"real", "synthetic"}:
        raise ValueError("data_origin은 real 또는 synthetic이어야 합니다.")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    files = _input_files(input_paths)
    if not files:
        raise ValueError("검사할 촬영 이미지가 없습니다.")
    layout = load_layout(layout_path)
    identifier = PageIdentifier(blank_dir=blank_dir, layout_path=layout_path, dpi=options.dpi)
    manual = load_manual_corners(manual_corners_path)

    assessments: list[PhotoAssessment] = []
    for path in files:
        try:
            result, _ = assess_photo(path, identifier=identifier, layout=layout, options=options, manual=manual)
        except Exception as error:
            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            height, width = image.shape[:2] if image is not None else (0, 0)
            result = PhotoAssessment(
                input_path=path, width=width, height=height,
                megapixels=width * height / 1_000_000.0 if width and height else 0.0,
                page=None, status="blocked", score=0.0, reasons=["marker-failed"],
                actions=[ACTION_TEXT["marker-failed"]], error=str(error),
            )
        assessments.append(result)

    by_page: dict[int, list[PhotoAssessment]] = {}
    for result in assessments:
        if result.page is not None and result.status != "blocked":
            by_page.setdefault(result.page, []).append(result)
    selected: dict[int, PhotoAssessment] = {
        page: max(items, key=lambda item: (-STATUS_ORDER[item.status], item.score, item.page_confidence))
        for page, items in by_page.items()
    }
    expected = set(options.expected_pages)
    missing_pages = sorted(expected - set(selected))
    selected_statuses = [item.status for item in selected.values()]
    if missing_pages or any(item.status == "blocked" for item in assessments):
        session_status = "blocked"
    elif any(status == "retake" for status in selected_statuses):
        session_status = "retake"
    elif any(status == "review" for status in selected_statuses):
        session_status = "review"
    else:
        session_status = "accept"

    status_counts = {status: sum(1 for item in assessments if item.status == status) for status in STATUS_ORDER}
    report = {
        "schema_version": "1.9.0",
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "data_origin": options.data_origin,
        "profile": options.profile,
        "thresholds": asdict(options.thresholds),
        "input_files": len(files),
        "session_status": session_status,
        "status_counts": status_counts,
        "selected_pages": sorted(selected),
        "missing_pages": missing_pages,
        "duplicate_pages": sorted(page for page, items in by_page.items() if len(items) > 1),
        "photos": [item.to_dict() for item in assessments],
        "selected": {str(page): item.to_dict() for page, item in selected.items()},
        "truth_note": (
            "실제 사용자 촬영 데이터 결과" if options.data_origin == "real"
            else "합성 촬영 조건 결과이며 실사용 성공률로 해석하면 안 됨"
        ),
    }
    (output / "preflight-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    photo_rows = []
    for item in assessments:
        row = item.to_dict()
        row["input"] = row.pop("input_path")
        row["reasons"] = "|".join(item.reasons)
        row["actions"] = "|".join(item.actions)
        row.pop("marker_points", None)
        photo_rows.append(row)
    fields = [
        "input", "page", "status", "score", "width", "height", "megapixels",
        "marker_method", "marker_confidence", "page_confidence", "sharpness", "exposure",
        "glare", "shadow", "perspective", "page_coverage", "highlight_clip", "dark_clip",
        "reasons", "actions", "error",
    ]
    _write_csv(output / "photo-results.csv", photo_rows, fields)

    retake_rows: list[dict[str, Any]] = []
    for item in assessments:
        if item.status not in {"retake", "blocked"}:
            continue
        retake_rows.append({
            "page": item.page or "",
            "input": str(item.input_path),
            "status": item.status,
            "score": round(item.score, 2),
            "reasons": "|".join(item.reasons),
            "actions": "|".join(item.actions),
        })
    for page in missing_pages:
        retake_rows.append({
            "page": page, "input": "", "status": "blocked", "score": 0,
            "reasons": "missing-page", "actions": ACTION_TEXT["missing-page"],
        })
    _write_csv(output / "retake-list.csv", retake_rows, ["page", "input", "status", "score", "reasons", "actions"])
    overview = _build_overview(assessments, output / "preflight-overview.png")
    html_path = _build_html(report, output / "preflight-report.html")
    report["files"] = {
        "json": "preflight-report.json", "photo_csv": "photo-results.csv",
        "retake_csv": "retake-list.csv", "html": html_path.name,
        "overview": overview.name if overview else None,
    }
    (output / "preflight-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
