from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunOptions:
    dpi: int = 150
    data_origin: str = "real"
    family_name: str = "HandFont Studio"
    style_name: str = "Regular"
    vectorize_limit: int | None = None
    compose_limit: int = 64
    allow_retake: bool = False
    resume: bool = False
    keep_intermediate_font: bool = False
    expected_pages: tuple[int, ...] = tuple(range(1, 10))

    def validate(self) -> None:
        if self.dpi not in {150, 200, 300, 400}:
            raise ValueError("dpi는 150, 200, 300, 400 중 하나여야 합니다.")
        if self.data_origin not in {"real", "synthetic"}:
            raise ValueError("data_origin은 real 또는 synthetic이어야 합니다.")
        if self.vectorize_limit is not None and self.vectorize_limit < 1:
            raise ValueError("vectorize_limit은 1 이상 또는 None이어야 합니다.")
        if self.compose_limit < 0:
            raise ValueError("compose_limit은 0 이상이어야 합니다.")
        if not self.family_name.strip():
            raise ValueError("family_name은 비어 있을 수 없습니다.")
        if not self.expected_pages:
            raise ValueError("expected_pages는 비어 있을 수 없습니다.")
        if len(set(self.expected_pages)) != len(self.expected_pages):
            raise ValueError("expected_pages에는 중복 페이지를 지정할 수 없습니다.")
        if any(page < 1 or page > 9 for page in self.expected_pages):
            raise ValueError("expected_pages는 1~9 범위여야 합니다.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StageResult:
    name: str
    status: str
    started_at: str
    finished_at: str
    duration_seconds: float
    output_dir: str | None = None
    summary_file: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunArtifacts:
    output_root: Path
    preflight_dir: Path
    ingest_dir: Path
    source_masks_dir: Path
    composition_dir: Path
    font_validation_dir: Path
    direct_manifest: Path
    combined_manifest: Path
    report_json: Path
    normalized_report_json: Path
    report_html: Path

    @classmethod
    def under(cls, output_root: Path) -> "RunArtifacts":
        return cls(
            output_root=output_root,
            preflight_dir=output_root / "01-preflight",
            ingest_dir=output_root / "02-ingest",
            source_masks_dir=output_root / "03-source-masks",
            composition_dir=output_root / "04-composition",
            font_validation_dir=output_root / "05-font-validation",
            direct_manifest=output_root / "02-ingest" / "captured-glyph-manifest.json",
            combined_manifest=output_root / "05-font-validation" / "combined-glyph-manifest.json",
            report_json=output_root / "run-report.json",
            normalized_report_json=output_root / "run-report.normalized.json",
            report_html=output_root / "run-report.html",
        )
