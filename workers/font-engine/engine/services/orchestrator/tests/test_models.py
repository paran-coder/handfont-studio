from pathlib import Path

import pytest

from handfont_orchestrator.models import RunArtifacts, RunOptions


def test_run_options_validation():
    RunOptions(dpi=150, data_origin="synthetic", compose_limit=0).validate()
    with pytest.raises(ValueError):
        RunOptions(dpi=123).validate()
    with pytest.raises(ValueError):
        RunOptions(data_origin="unknown").validate()
    with pytest.raises(ValueError):
        RunOptions(vectorize_limit=0).validate()


def test_artifact_layout(tmp_path: Path):
    artifacts = RunArtifacts.under(tmp_path)
    assert artifacts.preflight_dir.name == "01-preflight"
    assert artifacts.report_json == tmp_path / "run-report.json"


def test_expected_pages_validation():
    RunOptions(expected_pages=(1, 2, 3)).validate()
    with pytest.raises(ValueError):
        RunOptions(expected_pages=()).validate()
    with pytest.raises(ValueError):
        RunOptions(expected_pages=(1, 1)).validate()
    with pytest.raises(ValueError):
        RunOptions(expected_pages=(0, 1)).validate()
