from pathlib import Path
import json

from handfont_hangul_composer.benchmark import select_benchmark_characters


ROOT = Path(__file__).resolve().parents[2]
POSITION_MAP = ROOT / "hangul-engine" / "examples" / "hangul-source-v1.6.0" / "hangul-position-map.json"


def test_benchmark_has_500_unique_unwritten_syllables():
    data = json.loads(POSITION_MAP.read_text(encoding="utf-8"))
    representative = {entry["character"] for entry in data["entries"]}
    forms = {component["form_id"] for entry in data["entries"] for component in entry["components"]}
    selected = select_benchmark_characters(representative, forms)
    assert len(selected) == 500
    assert len(set(selected)) == 500
    assert representative.isdisjoint(selected)
