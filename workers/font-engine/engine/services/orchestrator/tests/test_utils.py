from pathlib import Path

from handfont_orchestrator.utils import count_font_binaries, normalized_report, remove_font_binaries


def test_remove_font_binaries(tmp_path: Path):
    (tmp_path / "a.ttf").write_bytes(b"font")
    (tmp_path / "b.txt").write_text("keep")
    removed = remove_font_binaries(tmp_path)
    assert removed == ["a.ttf"]
    assert count_font_binaries(tmp_path) == 0
    assert (tmp_path / "b.txt").exists()


def test_normalized_report_drops_time_fields():
    payload = {"started_at": "x", "stage": {"duration_seconds": 1.2, "value": 3}}
    assert normalized_report(payload) == {"stage": {"value": 3}}


def test_semantic_options_can_ignore_resume_flag():
    from handfont_orchestrator.models import RunOptions
    options = RunOptions(resume=True).to_dict()
    options.pop("resume")
    assert "resume" not in options
    assert options["family_name"] == "HandFont Studio"
