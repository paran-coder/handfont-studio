from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset import generate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(prog="handfont-hangul-engine")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--charset", type=Path, required=True)
    parser.add_argument("--vectorizer-root", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    args = parser.parse_args()
    manifest = generate_dataset(args.output, args.charset, args.vectorizer_root, args.font)
    print(json.dumps({k: manifest[k] for k in ("requested_glyphs", "generated_glyphs", "failures")}, ensure_ascii=False, indent=2))
    return 1 if manifest["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
