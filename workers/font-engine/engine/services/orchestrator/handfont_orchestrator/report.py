from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .utils import write_json


def render_html(report: dict[str, Any], output: Path) -> Path:
    stages = report.get("stages", [])
    rows = []
    for stage in stages:
        metrics = stage.get("metrics", {})
        metrics_text = "<br>".join(f"<b>{html.escape(str(k))}</b>: {html.escape(str(v))}" for k, v in metrics.items())
        warning_text = "<br>".join(html.escape(str(v)) for v in stage.get("warnings", []))
        rows.append(
            "<tr>"
            f"<td>{html.escape(stage['name'])}</td>"
            f"<td><span class='status {html.escape(stage['status'])}'>{html.escape(stage['status'])}</span></td>"
            f"<td>{stage.get('duration_seconds', 0):.3f}s</td>"
            f"<td>{metrics_text}</td>"
            f"<td>{warning_text or html.escape(str(stage.get('error') or ''))}</td>"
            "</tr>"
        )
    truth = report.get("truth_note", "")
    body = f"""<!doctype html>
<html lang='ko'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>HandFont Studio v2.1.0 실행 보고서</title>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f6f8;color:#15171a}}
main{{max-width:1180px;margin:0 auto;padding:40px 24px 64px}}h1{{font-size:30px;margin:0 0 8px}}.meta{{color:#5b6470;margin-bottom:26px}}
.card{{background:#fff;border:1px solid #e1e5ea;border-radius:16px;padding:22px;margin-bottom:20px;box-shadow:0 8px 24px rgba(20,30,50,.05)}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #e7eaf0;vertical-align:top}}th{{font-size:13px;color:#58606b}}
.status{{display:inline-block;padding:4px 9px;border-radius:999px;font-weight:700;font-size:12px;background:#e8ebef}}.completed,.accept{{background:#e3f5e8;color:#176b31}}.review{{background:#fff3cc;color:#725600}}.stopped,.retake{{background:#ffe1d8;color:#8a2c14}}.failed,.blocked{{background:#ececef;color:#24262a}}
code{{background:#f0f2f5;padding:2px 5px;border-radius:5px}}ul{{line-height:1.7}}
</style></head><body><main>
<h1>HandFont Studio v2.1.0</h1><div class='meta'>상태: <b>{html.escape(report.get('status','unknown'))}</b> · 데이터: <b>{html.escape(report.get('data_origin','unknown'))}</b></div>
<div class='card'><h2>사실성 메모</h2><p>{html.escape(truth)}</p></div>
<div class='card'><h2>단계 결과</h2><table><thead><tr><th>단계</th><th>상태</th><th>시간</th><th>지표</th><th>경고·오류</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class='card'><h2>폰트 바이너리 정책</h2><p>내부 검증용 폰트는 검사 후 삭제합니다. 보고서에는 SHA-256과 렌더링 결과만 남습니다.</p><p>삭제한 파일: <code>{html.escape(str(report.get('font_policy',{}).get('removed',[])))}</code></p></div>
</main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    return output
