from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from .manifests import build_captured_manifest, export_representative_masks, merge_manifests
from .models import RunArtifacts, RunOptions, StageResult
from .paths import ServicePaths
from .report import render_html
from .utils import (
    count_font_binaries,
    ensure_clean_output,
    env_metadata,
    normalized_report,
    read_json,
    relative,
    remove_font_binaries,
    sha256_file,
    utc_now,
    write_json,
)


class PipelineStopped(RuntimeError):
    pass


def _run_stage(
    name: str,
    output_root: Path,
    function: Callable[[], tuple[dict[str, Any], Path | None, list[str]]],
    *,
    output_dir: Path | None = None,
    cached: bool = False,
) -> tuple[StageResult, dict[str, Any]]:
    started = utc_now()
    start_clock = time.perf_counter()
    try:
        metrics, summary_path, warnings = function()
        status = "review" if warnings else "completed"
        result = StageResult(
            name=name,
            status=status,
            started_at=started,
            finished_at=utc_now(),
            duration_seconds=round(time.perf_counter() - start_clock, 6),
            output_dir=relative(output_dir, output_root) if output_dir else None,
            summary_file=relative(summary_path, output_root),
            metrics=metrics,
            warnings=warnings,
            cached=cached,
        )
        return result, metrics
    except PipelineStopped as error:
        result = StageResult(
            name=name,
            status="stopped",
            started_at=started,
            finished_at=utc_now(),
            duration_seconds=round(time.perf_counter() - start_clock, 6),
            output_dir=relative(output_dir, output_root) if output_dir else None,
            error=str(error),
            cached=cached,
        )
        return result, {}
    except Exception as error:
        result = StageResult(
            name=name,
            status="failed",
            started_at=started,
            finished_at=utc_now(),
            duration_seconds=round(time.perf_counter() - start_clock, 6),
            output_dir=relative(output_dir, output_root) if output_dir else None,
            error=f"{type(error).__name__}: {error}",
            cached=cached,
        )
        return result, {}


def _input_inventory(inputs: list[Path]) -> list[dict[str, Any]]:
    supported = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
    files: list[Path] = []
    for item in inputs:
        if item.is_dir():
            files.extend(path for path in sorted(item.iterdir()) if path.suffix.lower() in supported)
        elif item.is_file():
            files.append(item)
    unique = []
    seen: set[Path] = set()
    for path in files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append({
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return unique


def run_pipeline(
    inputs: list[Path],
    output_root: Path,
    options: RunOptions,
    *,
    manual_corners: Path | None = None,
    paths: ServicePaths | None = None,
) -> dict[str, Any]:
    options.validate()
    ensure_clean_output(output_root, options.resume)
    artifacts = RunArtifacts.under(output_root)
    paths = paths or ServicePaths.discover()
    paths.bootstrap_imports()

    from handfont_capture.field_validation import FieldOptions, preflight_capture_session
    from handfont_capture.models import SessionOptions
    from handfont_capture.session import process_capture_session
    from handfont_fontbuilder.builder import build_font
    from handfont_fontbuilder.models import FontBuildOptions
    from handfont_fontbuilder.validation import validate_and_render
    from handfont_hangul_composer.pipeline import run_benchmark

    position_map = paths.hangul_engine / "examples" / "hangul-source-v1.6.0" / "hangul-position-map.json"
    inventory = _input_inventory(inputs)
    request_options = options.to_dict()
    request_options.pop("resume", None)
    request_payload = {
        "schema_version": "2.1.0",
        "input_inventory": inventory,
        "manual_corners": (
            {"name": manual_corners.name, "sha256": sha256_file(manual_corners)}
            if manual_corners and manual_corners.exists() else None
        ),
        "options": request_options,
    }
    request_path = output_root / "run-request.json"
    if options.resume and request_path.exists():
        previous_request = read_json(request_path)
        if previous_request != request_payload:
            raise ValueError("--resume 요청이 기존 실행의 입력 또는 옵션과 다릅니다. 새 출력 폴더를 사용하십시오.")
    else:
        write_json(request_path, request_payload)

    report: dict[str, Any] = {
        "schema_version": "2.1.0",
        "project": "HandFont Studio",
        "version": "2.1.0",
        "status": "running",
        "started_at": utc_now(),
        "data_origin": options.data_origin,
        "truth_note": (
            "실제 사용자 촬영 데이터 결과" if options.data_origin == "real"
            else "합성 촬영 조건 결과이며 실사용 성공률로 해석하면 안 됨"
        ),
        "options": options.to_dict(),
        "environment": env_metadata(),
        "input_inventory": inventory,
        "manual_corners": manual_corners.name if manual_corners else None,
        "stages": [],
        "artifacts": {},
    }

    def finalize(status: str) -> dict[str, Any]:
        report["status"] = status
        report["finished_at"] = utc_now()
        report["artifacts"] = {
            "preflight": relative(artifacts.preflight_dir / "preflight-report.json", output_root),
            "ingest": relative(artifacts.ingest_dir / "session-summary.json", output_root),
            "captured_manifest": relative(artifacts.direct_manifest, output_root),
            "source_masks": relative(artifacts.source_masks_dir / "source-mask-report.json", output_root),
            "composition": relative(artifacts.composition_dir / "benchmark-summary.json", output_root),
            "combined_manifest": relative(artifacts.combined_manifest, output_root),
            "font_validation": relative(artifacts.font_validation_dir / "font-validation.json", output_root),
            "html": artifacts.report_html.name,
        }
        report.setdefault("font_policy", {})
        write_json(artifacts.report_json, report)
        normalized = normalized_report(report)
        write_json(artifacts.normalized_report_json, normalized)
        report["normalized_report_sha256"] = sha256_file(artifacts.normalized_report_json)
        write_json(artifacts.report_json, report)
        render_html(report, artifacts.report_html)
        return report

    # 1. Preflight
    preflight_cached = options.resume and (artifacts.preflight_dir / "preflight-report.json").exists()

    def preflight_stage() -> tuple[dict[str, Any], Path, list[str]]:
        if preflight_cached:
            result = read_json(artifacts.preflight_dir / "preflight-report.json")
        else:
            result = preflight_capture_session(
                inputs,
                artifacts.preflight_dir,
                FieldOptions(dpi=options.dpi, expected_pages=options.expected_pages, data_origin=options.data_origin),
                manual_corners_path=manual_corners,
            )
        status = result["session_status"]
        warnings = []
        if status == "review":
            warnings.append("촬영 품질 검수 항목이 있으나 처리를 계속합니다.")
        if status == "blocked":
            raise PipelineStopped("사전 검사 상태가 blocked입니다. 누락 페이지 또는 마커 실패를 수정해야 합니다.")
        if status == "retake" and not options.allow_retake:
            raise PipelineStopped("사전 검사 상태가 retake입니다. 재촬영하거나 --allow-retake를 사용해야 합니다.")
        if status == "retake":
            warnings.append("재촬영 권장 상태를 override하여 계속합니다.")
        return {
            "session_status": status,
            "input_files": result["input_files"],
            "selected_pages": len(result["selected_pages"]),
            "missing_pages": result["missing_pages"],
            "status_counts": result["status_counts"],
        }, artifacts.preflight_dir / "preflight-report.json", warnings

    stage, _ = _run_stage("preflight", output_root, preflight_stage, output_dir=artifacts.preflight_dir, cached=preflight_cached)
    report["stages"].append(stage.to_dict())
    if stage.status in {"stopped", "failed"}:
        return finalize(stage.status)

    # 2. Capture ingest and vectorization
    ingest_cached = options.resume and (artifacts.ingest_dir / "session-summary.json").exists()

    def ingest_stage() -> tuple[dict[str, Any], Path, list[str]]:
        if ingest_cached:
            result = read_json(artifacts.ingest_dir / "session-summary.json")
        else:
            result = process_capture_session(
                inputs,
                artifacts.ingest_dir,
                SessionOptions(
                    dpi=options.dpi,
                    vectorize=True,
                    vectorize_limit=options.vectorize_limit,
                    expected_pages=options.expected_pages,
                ),
                manual_corners_path=manual_corners,
            )
        if not result.get("complete"):
            raise PipelineStopped(f"촬영 세션이 완전하지 않습니다. missing_pages={result.get('missing_pages')}")
        warnings = []
        failures = result.get("vectorization", {}).get("failed_or_skipped", 0)
        if failures:
            warnings.append(f"벡터화 실패 또는 건너뜀 {failures}건")
        return {
            "selected_pages": len(result.get("selected_pages", [])),
            "duplicate_pages": result.get("duplicate_pages", []),
            "manual_pages": result.get("manual_pages", []),
            "cell_status_counts": result.get("cell_status_counts", {}),
            "vectorized": result.get("vectorization", {}).get("processed", 0),
            "vector_failed_or_skipped": failures,
            "position_coverage": result.get("position_coverage", {}),
        }, artifacts.ingest_dir / "session-summary.json", warnings

    stage, _ = _run_stage("capture-ingest", output_root, ingest_stage, output_dir=artifacts.ingest_dir, cached=ingest_cached)
    report["stages"].append(stage.to_dict())
    if stage.status in {"stopped", "failed"}:
        return finalize(stage.status)

    # 3. Captured manifest
    manifest_cached = options.resume and artifacts.direct_manifest.exists()

    def captured_manifest_stage() -> tuple[dict[str, Any], Path, list[str]]:
        result = read_json(artifacts.direct_manifest) if manifest_cached else build_captured_manifest(artifacts.ingest_dir, artifacts.direct_manifest)
        if not result.get("glyph_count"):
            raise PipelineStopped("폰트 빌드에 사용할 캡처 글리프가 없습니다.")
        warnings = [f"manifest에서 {len(result.get('skipped', []))}개 항목을 제외했습니다."] if result.get("skipped") else []
        return {"glyph_count": result["glyph_count"], "skipped": len(result.get("skipped", []))}, artifacts.direct_manifest, warnings

    stage, _ = _run_stage("captured-manifest", output_root, captured_manifest_stage, output_dir=artifacts.ingest_dir, cached=manifest_cached)
    report["stages"].append(stage.to_dict())
    if stage.status in {"stopped", "failed"}:
        return finalize(stage.status)

    # 4. Representative source masks
    source_cached = options.resume and (artifacts.source_masks_dir / "source-mask-report.json").exists()

    def source_mask_stage() -> tuple[dict[str, Any], Path, list[str]]:
        result = read_json(artifacts.source_masks_dir / "source-mask-report.json") if source_cached else export_representative_masks(artifacts.ingest_dir, position_map, artifacts.source_masks_dir)
        warnings = []
        if result["missing_count"]:
            warnings.append(f"대표 한글 마스크 {result['missing_count']}개가 누락되어 자동 조합을 건너뜁니다.")
        return {"required": result["required"], "copied": result["copied"], "missing": result["missing_count"]}, artifacts.source_masks_dir / "source-mask-report.json", warnings

    stage, source_metrics = _run_stage("representative-masks", output_root, source_mask_stage, output_dir=artifacts.source_masks_dir, cached=source_cached)
    report["stages"].append(stage.to_dict())
    if stage.status == "failed":
        return finalize("failed")

    # 5. Hangul composition benchmark
    composition_manifest = artifacts.composition_dir / "composed-glyph-manifest.json"
    composition_cached = options.resume and (artifacts.composition_dir / "benchmark-summary.json").exists()

    def composition_stage() -> tuple[dict[str, Any], Path | None, list[str]]:
        if options.compose_limit == 0:
            return {"requested": 0, "generated": 0, "skipped": True}, None, ["compose_limit=0으로 자동 조합을 건너뛰었습니다."]
        if source_metrics.get("missing", 1):
            return {"requested": options.compose_limit, "generated": 0, "skipped": True}, None, ["대표 한글 마스크가 누락되어 자동 조합을 건너뛰었습니다."]
        if composition_cached:
            result = read_json(artifacts.composition_dir / "benchmark-summary.json")
        else:
            result = run_benchmark(
                position_map=position_map,
                source_masks=artifacts.source_masks_dir,
                output_dir=artifacts.composition_dir,
                vectorizer_root=paths.glyph_vectorizer,
                font_builder_root=None,
                reference_font=None,
                limit=options.compose_limit,
            )
        failures = len(result.get("failures", []))
        warnings = [f"자동 조합 실패 {failures}건"] if failures else []
        return {
            "requested": result.get("benchmark_requested", options.compose_limit),
            "generated": result.get("benchmark_generated", 0),
            "failures": failures,
            "review_count": result.get("review_count", 0),
            "mean_quality": result.get("metrics", {}).get("quality_score", {}).get("mean"),
            "mean_vector_iou": result.get("metrics", {}).get("vector_iou", {}).get("mean"),
        }, artifacts.composition_dir / "benchmark-summary.json", warnings

    stage, composition_metrics = _run_stage("hangul-composition", output_root, composition_stage, output_dir=artifacts.composition_dir, cached=composition_cached)
    report["stages"].append(stage.to_dict())
    if stage.status == "failed":
        return finalize("failed")

    # 6. Merge and internal font validation
    font_cached = options.resume and (artifacts.font_validation_dir / "font-validation.json").exists() and artifacts.combined_manifest.exists()

    def font_stage() -> tuple[dict[str, Any], Path, list[str]]:
        artifacts.font_validation_dir.mkdir(parents=True, exist_ok=True)
        manifests = [artifacts.direct_manifest]
        if composition_manifest.exists() and composition_metrics.get("generated", 0):
            manifests.append(composition_manifest)
        combined = merge_manifests(manifests, artifacts.combined_manifest)
        if font_cached:
            validation = read_json(artifacts.font_validation_dir / "font-validation.json")
            build_report = read_json(artifacts.font_validation_dir / "font-build-report.json")
            removed = remove_font_binaries(artifacts.font_validation_dir)
        else:
            build_report = build_font(
                artifacts.combined_manifest,
                artifacts.font_validation_dir,
                FontBuildOptions(
                    family_name=options.family_name,
                    style_name=options.style_name,
                    version="2.1.0",
                    output_basename="HandFont-Integrated-Internal",
                ),
            )
            font_path = artifacts.font_validation_dir / build_report["font"]
            validation = validate_and_render(font_path, artifacts.font_validation_dir)
            internal_sha = sha256_file(font_path)
            build_report["internal_font_sha256"] = internal_sha
            write_json(artifacts.font_validation_dir / "font-build-report.json", build_report)
            removed = [] if options.keep_intermediate_font else remove_font_binaries(artifacts.font_validation_dir)
        report["font_policy"] = {
            "keep_intermediate_font": options.keep_intermediate_font,
            "removed": removed,
            "remaining_font_binaries": count_font_binaries(artifacts.font_validation_dir),
            "internal_font_sha256": build_report.get("internal_font_sha256", build_report.get("sha256")),
        }
        if not options.keep_intermediate_font and report["font_policy"]["remaining_font_binaries"]:
            raise RuntimeError("검증 후 폰트 바이너리가 남아 있습니다.")
        violations = (
            len(validation.get("empty_outlines", []))
            + len(validation.get("metric_violations", []))
            + len(validation.get("hangul_width_violations", []))
            + len(validation.get("empty_rendered_glyphs", []))
            + len(build_report.get("missing_tables", []))
            + len(build_report.get("bounds_violations", []))
        )
        warnings = [f"폰트 검증 위반 {violations}건"] if violations else []
        return {
            "combined_glyphs": combined["glyph_count"],
            "manifest_conflicts": len(combined["conflicts"]),
            "font_glyph_count": build_report.get("glyph_count"),
            "cmap_count": validation.get("cmap_count"),
            "hangul_cmap_count": validation.get("hangul_cmap_count"),
            "validation_violations": violations,
            "font_removed": not options.keep_intermediate_font,
        }, artifacts.font_validation_dir / "font-validation.json", warnings

    stage, _ = _run_stage("font-build-validation", output_root, font_stage, output_dir=artifacts.font_validation_dir, cached=font_cached)
    report["stages"].append(stage.to_dict())
    if stage.status == "failed":
        return finalize("failed")

    final_status = "review" if any(item["status"] == "review" for item in report["stages"]) else "completed"
    return finalize(final_status)
