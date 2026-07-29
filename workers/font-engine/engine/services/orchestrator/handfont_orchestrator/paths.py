from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServicePaths:
    project_root: Path
    services_root: Path
    capture_ingest: Path
    image_pipeline: Path
    glyph_vectorizer: Path
    hangul_engine: Path
    hangul_composer: Path
    font_builder: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> "ServicePaths":
        anchor = (start or Path(__file__)).resolve()
        project_root = anchor.parents[3]
        services_root = project_root / "services"
        values = cls(
            project_root=project_root,
            services_root=services_root,
            capture_ingest=services_root / "capture-ingest",
            image_pipeline=services_root / "image-pipeline",
            glyph_vectorizer=services_root / "glyph-vectorizer",
            hangul_engine=services_root / "hangul-engine",
            hangul_composer=services_root / "hangul-composer",
            font_builder=services_root / "font-builder",
        )
        missing = [str(path) for path in (
            values.capture_ingest,
            values.image_pipeline,
            values.glyph_vectorizer,
            values.hangul_engine,
            values.hangul_composer,
            values.font_builder,
        ) if not path.exists()]
        if missing:
            raise FileNotFoundError(f"필수 서비스 폴더가 없습니다: {missing}")
        return values

    def bootstrap_imports(self) -> None:
        for path in (
            self.capture_ingest,
            self.image_pipeline,
            self.glyph_vectorizer,
            self.hangul_engine,
            self.hangul_composer,
            self.font_builder,
        ):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)
