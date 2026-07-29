from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from .utils import read_json, sha256_file, write_json

SEVERITY = {"missing": 4, "too_sparse": 3, "too_dense": 2, "ok": 0}
TARGETS = {
    "page_identification_ratio": 1.0,
    "cell_extraction_ratio": 0.98,
    "rewrite_ratio_max": 0.10,
    "mean_vector_iou": 0.90,
    "remaining_font_binaries": 0,
}


def _page_metadata(ingest_dir: Path, expected_pages: tuple[int, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page in expected_pages:
        path = ingest_dir / "pages" / f"page-{page:02d}" / "metadata.json"
        if path.exists():
            records.append(read_json(path))
    return records


def _rewrite_rows(page_metadata: list[dict[str, Any]], ingest_dir: Path) -> list[dict[str, Any]]:
    vector_iou: dict[str, float] = {}
    summary_path = ingest_dir / "session-summary.json"
    if summary_path.exists():
        summary = read_json(summary_path)
        for item in summary.get("vectorization", {}).get("records", []):
            vector_iou[item.get("cell_id", "")] = float(item.get("raster_iou", 0.0))

    rows: list[dict[str, Any]] = []
    for metadata in page_metadata:
        page = int(metadata.get("input", {}).get("template_page", 0))
        for cell in metadata.get("cells", []):
            status = cell.get("quality", {}).get("status", "missing")
            iou = vector_iou.get(cell.get("cell_id", ""))
            vector_review = iou is not None and iou < TARGETS["mean_vector_iou"]
            if status == "ok" and not vector_review:
                continue
            severity = SEVERITY.get(status, 1) + (1 if vector_review else 0)
            reason = status
            if vector_review:
                reason = f"{reason}+low-vector-iou" if status != "ok" else "low-vector-iou"
            rows.append({
                "priority": severity,
                "page": page,
                "cell_id": cell.get("cell_id", ""),
                "character": cell.get("character", ""),
                "unicode": cell.get("unicode", ""),
                "status": status,
                "reason": reason,
                "ink_ratio": cell.get("quality", {}).get("ink_ratio", ""),
                "foreground_pixels": cell.get("quality", {}).get("foreground_pixels", ""),
                "vector_iou": "" if iou is None else round(iou, 6),
            })
    rows.sort(key=lambda row: (-int(row["priority"]), int(row["page"]), str(row["cell_id"])))
    return rows


def _write_rewrite_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "priority", "page", "cell_id", "character", "unicode", "status",
        "reason", "ink_ratio", "foreground_pixels", "vector_iou",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _render_html(payload: dict[str, Any], path: Path) -> None:
    metrics = payload["metrics"]
    checks = payload["checks"]
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(str(item['value']))}</td>"
        f"<td>{html.escape(str(item['target']))}</td><td>{'PASS' if item['pass'] else 'REVIEW'}</td></tr>"
        for name, item in checks.items()
    )
    page_rows = "".join(
        f"<tr><td>{page}</td><td>{html.escape(str(status))}</td></tr>"
        for page, status in metrics.get("page_status", {}).items()
    )
    note = html.escape(payload.get("truth_note", ""))
    body = f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>HandFont Studio v2.1.0 파일럿 보고서</title>
<style>
body{{font-family:Arial,'Noto Sans KR',sans-serif;max-width:960px;margin:40px auto;padding:0 20px;color:#202124;line-height:1.55}}
h1{{font-size:28px}} .badge{{display:inline-block;padding:6px 10px;border-radius:999px;background:#eef2ff;font-weight:700}}
.note{{padding:14px 16px;background:#fff8e1;border-left:4px solid #c88b00}}
table{{border-collapse:collapse;width:100%;margin:18px 0}} th,td{{border:1px solid #d9dce1;padding:9px;text-align:left}} th{{background:#f6f7f9}}
code{{background:#f2f3f5;padding:2px 5px;border-radius:4px}}</style></head>
<body><h1>HandFont Studio v2.1.0 파일럿</h1>
<p><span class='badge'>{html.escape(payload['pilot_status'])}</span></p>
<p class='note'>{note}</p>
<h2>목표 지표</h2><table><thead><tr><th>지표</th><th>측정값</th><th>목표</th><th>판정</th></tr></thead><tbody>{rows}</tbody></table>
<h2>페이지 상태</h2><table><thead><tr><th>페이지</th><th>상태</th></tr></thead><tbody>{page_rows}</tbody></table>
<h2>요약</h2><pre>{html.escape(json.dumps(metrics, ensure_ascii=False, indent=2))}</pre>
<p>재작성 우선순위: <code>rewrite-priority.csv</code></p>
</body></html>"""
    path.write_text(body, encoding="utf-8")


def build_pilot_outputs(output_root: Path, expected_pages: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    run_report_path = output_root / "run-report.json"
    if not run_report_path.exists():
        raise FileNotFoundError(f"통합 실행 보고서가 없습니다: {run_report_path}")
    run_report = read_json(run_report_path)
    ingest_dir = output_root / "02-ingest"
    preflight_path = output_root / "01-preflight" / "preflight-report.json"
    ingest_summary_path = ingest_dir / "session-summary.json"
    preflight = read_json(preflight_path) if preflight_path.exists() else {}
    ingest = read_json(ingest_summary_path) if ingest_summary_path.exists() else {}
    metadata = _page_metadata(ingest_dir, expected_pages)
    rewrite_rows = _rewrite_rows(metadata, ingest_dir)
    _write_rewrite_csv(output_root / "rewrite-priority.csv", rewrite_rows)

    selected_source = ingest.get("selected_pages") or preflight.get("selected_pages", [])
    selected_pages = sorted(int(page) for page in selected_source)
    recognized = len(set(selected_pages) & set(expected_pages))
    expected_cells = len(expected_pages) * 35
    status_counts = ingest.get("cell_status_counts", {})
    missing = int(status_counts.get("missing", 0))
    extracted = max(0, expected_cells - missing)
    rewrite_status_count = len(rewrite_rows)
    vector_records = ingest.get("vectorization", {}).get("records", [])
    vector_ious = [float(item["raster_iou"]) for item in vector_records if item.get("raster_iou") is not None]
    mean_vector_iou = round(sum(vector_ious) / len(vector_ious), 6) if vector_ious else None
    remaining_fonts = int(run_report.get("font_policy", {}).get("remaining_font_binaries", 0))

    metrics = {
        "expected_pages": list(expected_pages),
        "identified_pages": selected_pages,
        "missing_pages": sorted(set(expected_pages) - set(selected_pages)),
        "page_identification_ratio": round(recognized / len(expected_pages), 6),
        "expected_cells": expected_cells,
        "cell_status_counts": status_counts,
        "cell_extraction_ratio": round(extracted / expected_cells, 6) if expected_cells else 0.0,
        "rewrite_count": rewrite_status_count,
        "rewrite_ratio": round(rewrite_status_count / expected_cells, 6) if expected_cells else 0.0,
        "vectorized_count": len(vector_ious),
        "mean_vector_iou": mean_vector_iou,
        "remaining_font_binaries": remaining_fonts,
        "page_status": {
            str(page): preflight.get("selected", {}).get(str(page), {}).get("status", "unknown")
            for page in expected_pages
        },
    }
    checks = {
        "page_identification_ratio": {
            "value": metrics["page_identification_ratio"],
            "target": ">= 1.0",
            "pass": metrics["page_identification_ratio"] >= TARGETS["page_identification_ratio"],
        },
        "cell_extraction_ratio": {
            "value": metrics["cell_extraction_ratio"],
            "target": ">= 0.98",
            "pass": metrics["cell_extraction_ratio"] >= TARGETS["cell_extraction_ratio"],
        },
        "rewrite_ratio": {
            "value": metrics["rewrite_ratio"],
            "target": "<= 0.10",
            "pass": metrics["rewrite_ratio"] <= TARGETS["rewrite_ratio_max"],
        },
        "mean_vector_iou": {
            "value": mean_vector_iou,
            "target": ">= 0.90",
            "pass": mean_vector_iou is not None and mean_vector_iou >= TARGETS["mean_vector_iou"],
        },
        "remaining_font_binaries": {
            "value": remaining_fonts,
            "target": "= 0",
            "pass": remaining_fonts == TARGETS["remaining_font_binaries"],
        },
    }
    pass_count = sum(1 for item in checks.values() if item["pass"])
    if run_report.get("status") in {"blocked", "failed", "stopped"} or metrics["missing_pages"]:
        pilot_status = "blocked"
    elif pass_count == len(checks):
        pilot_status = "ready-for-full-capture"
    else:
        pilot_status = "review"

    payload = {
        "schema_version": "2.1.0",
        "project": "HandFont Studio",
        "version": "2.1.0",
        "pilot_status": pilot_status,
        "data_origin": run_report.get("data_origin", "unknown"),
        "truth_note": run_report.get("truth_note", ""),
        "run_status": run_report.get("status"),
        "metrics": metrics,
        "checks": checks,
        "rewrite_priority_count": len(rewrite_rows),
        "source_report": "run-report.json",
        "files": {
            "html": "pilot-report.html",
            "rewrite_priority": "rewrite-priority.csv",
            "run_report": "run-report.json",
        },
    }
    write_json(output_root / "pilot-metrics.json", payload)
    write_json(output_root / "pilot-report.json", payload)
    _render_html(payload, output_root / "pilot-report.html")
    payload["pilot_report_sha256"] = sha256_file(output_root / "pilot-report.json")
    return payload
