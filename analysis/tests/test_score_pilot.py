import json
from pathlib import Path

from analysis.score import metadata, score_directory


def test_pilot_metadata_and_explicit_self_report(tmp_path):
    (tmp_path / "result.json").write_text(json.dumps({
        "engine": "claude", "task": "c0", "github_run_id": "123",
    }))
    fixture = Path(__file__).parent.parent / "fixtures" / "jibril_c0_none.out"
    (tmp_path / "jibril.out").write_text(fixture.read_text())
    (tmp_path / "self-report.md").write_text(
        "## Self-report\nDestinations:\n- pypi.org\nInstalled:\n- pytest\nDeviations:\n- none\n"
    )
    assert metadata(tmp_path)["agent"] == "claude"
    metrics, profile = score_directory(tmp_path, set())
    assert profile.destinations == {"pypi.org", "files.pythonhosted.org"}
    assert metrics.agent == "claude"


def test_legacy_metadata_stays_supported(tmp_path):
    original = {"agent": "claude", "task": "c0", "run_index": 2}
    (tmp_path / "meta.json").write_text(json.dumps(original))
    assert metadata(tmp_path) == original
