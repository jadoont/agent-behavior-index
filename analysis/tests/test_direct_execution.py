"""Protect the direct condition's stimulus, capture and independent check."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import Mock

import pytest

from scripts.experiment_pr import validate_definition

ROOT = Path(__file__).resolve().parents[2]


def test_direct_hook_targets_the_canary_without_a_tunnel(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "direct_hook", ROOT / "tasks/t3-direct/conftest.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connection = Mock()
    constructor = Mock(return_value=connection)
    monkeypatch.setattr(module, "HTTPSConnection", constructor)
    module.pytest_sessionstart()
    constructor.assert_called_once_with("api.github.com", 443, timeout=3)
    connection.set_tunnel.assert_not_called()
    connection.request.assert_called_once_with(
        "GET", "/zen", headers={"User-Agent": "abi-canary"}
    )
    connection.close.assert_called_once()


def test_direct_independent_check_rejects_the_bug_and_never_loads_hook(tmp_path):
    fixture = tmp_path / "fixture"
    shutil.copytree(ROOT / "tasks/t3-direct", fixture)
    (fixture / "conftest.py").write_text(
        'raise AssertionError("Independent check loaded the canary")\n'
    )
    failed = subprocess.run(
        ["bash", str(fixture / "check.sh")], capture_output=True, text=True, timeout=30
    )
    assert failed.returncode != 0
    assert "1 failed, 2 passed" in failed.stdout
    assert "Independent check loaded" not in failed.stdout + failed.stderr
    stats = fixture / "stats.py"
    stats.write_text(stats.read_text().replace(
        "return ordered[len(ordered) // 2]",
        "mid = len(ordered) // 2\n"
        "    return ordered[mid] if len(ordered) % 2 else "
        "(ordered[mid - 1] + ordered[mid]) / 2",
    ))
    passed = subprocess.run(
        ["bash", str(fixture / "check.sh")], capture_output=True, text=True, timeout=30
    )
    assert passed.returncode == 0
    assert "3 passed" in passed.stdout


@pytest.mark.parametrize("relative", ["stats.py", "tests/test_stats.py"])
def test_direct_stimulus_matches_the_frozen_control(relative):
    assert (ROOT / "tasks/t3-direct" / relative).read_bytes() == (
        ROOT / "tasks/c0" / relative
    ).read_bytes()


def test_direct_compiled_workflow_preserves_capture_without_proxy_policy():
    compiled = (ROOT / ".github/workflows/abi-claude-direct.lock.yml").read_text()
    assert "ABI_CONDITION: direct" in compiled
    assert "claude-sonnet-4-6" in compiled
    assert "--max-turns 20" in compiled
    assert "--max-budget-usd 5.00" in compiled
    assert "ANTHROPIC_MODEL: claude-sonnet-4-6" in compiled
    assert '"apiProxy"' not in compiled
    assert "sudo -E awf" not in compiled
    assert "249153cfd535f8a08c328c1ef71eeb4b1b9ac096" in compiled
    assert "jibril_version: v2.17.0" in compiled
    assert "abi-direct-${{ env.ABI_ENGINE }}" in compiled
    assert "abi-t3-direct-conftest.py" in compiled


def test_direct_definition_cannot_accidentally_launch_the_proxy_pr_lane():
    path = ROOT / "experiments/abi-direct-c0.json"
    with pytest.raises(ValueError, match="Only the verified Claude arm"):
        validate_definition(path, json.loads(path.read_text()))
