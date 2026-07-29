from pathlib import Path

from handfont_hangul_composer.library import TemplateLibrary


ROOT = Path(__file__).resolve().parents[2]
HANGUL_SOURCE = ROOT / "hangul-engine" / "examples" / "hangul-source-v1.6.0"


def test_library_builds_175_forms(tmp_path):
    library = TemplateLibrary.build(
        HANGUL_SOURCE / "hangul-position-map.json",
        HANGUL_SOURCE / "masks",
        tmp_path,
    )
    assert len(library.records) == 175
    assert sum(record.candidate_count == 1 for record in library.records.values()) == 158
    assert all(mask.any() for mask in library.masks.values())
