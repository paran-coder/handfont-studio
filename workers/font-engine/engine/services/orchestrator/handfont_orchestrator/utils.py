from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_report(payload: dict[str, Any]) -> dict[str, Any]:
    drop_keys = {"started_at", "finished_at", "processed_at", "duration_seconds", "created_at", "cached", "removed"}

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: clean(item) for key, item in sorted(value.items()) if key not in drop_keys}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str):
            # Normalize absolute run paths while retaining stable relative artifacts.
            cwd = str(Path.cwd())
            return value.replace(cwd, "<cwd>") if cwd and cwd in value else value
        return value

    return clean(payload)


def remove_font_binaries(root: Path) -> list[str]:
    removed: list[str] = []
    extensions = {".ttf", ".otf", ".woff", ".woff2"}
    if not root.exists():
        return removed
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            removed.append(str(path.relative_to(root)))
            path.unlink()
    return sorted(removed)


def count_font_binaries(root: Path) -> int:
    extensions = {".ttf", ".otf", ".woff", ".woff2"}
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in extensions)


def ensure_clean_output(path: Path, resume: bool) -> None:
    if not path.exists():
        path.mkdir(parents=True)
        return
    if resume:
        return
    if any(path.iterdir()):
        raise FileExistsError(f"출력 폴더가 비어 있지 않습니다: {path}. --resume을 사용하거나 새 폴더를 지정하십시오.")


def env_metadata() -> dict[str, str]:
    return {
        "python": os.sys.version.split()[0],
        "platform": os.sys.platform,
    }
