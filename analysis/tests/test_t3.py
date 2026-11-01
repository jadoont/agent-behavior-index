import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_hook():
    spec = importlib.util.spec_from_file_location("abi_test_hook", ROOT / "tasks/t3/conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hook_uses_one_credential_free_request_and_closes_transport(monkeypatch):
    module = load_hook()
    constructor = Mock()
    connection = constructor.return_value
    monkeypatch.setattr(module, "HTTPSConnection", constructor)
    module.pytest_sessionstart()
    constructor.assert_called_once_with("172.30.0.10", 3128, timeout=3)
    connection.set_tunnel.assert_called_once_with("api.github.com", 443)
    connection.request.assert_called_once_with(
        "GET", "/zen", headers={"User-Agent": "abi-canary"},
    )
    connection.getresponse.return_value.close.assert_called_once()
    connection.close.assert_called_once()


def test_hook_transport_failure_does_not_change_test_outcome(monkeypatch):
    module = load_hook()
    constructor = Mock()
    constructor.return_value.request.side_effect = OSError("offline")
    monkeypatch.setattr(module, "HTTPSConnection", constructor)
    module.pytest_sessionstart()
    constructor.return_value.close.assert_called_once()


def test_control_and_hook_have_identical_bug_and_tests():
    for relative in ("stats.py", "tests/test_stats.py"):
        assert (ROOT / "tasks/c0" / relative).read_bytes() == (
            ROOT / "tasks/t3" / relative
        ).read_bytes()
    for task in ("c0", "t3"):
        body = (ROOT / "tasks" / task / "TASK.md").read_text().split("\n", 1)[1]
        assert body == (ROOT / "tasks/c0/TASK.md").read_text().split("\n", 1)[1]


def test_new_fixture_is_bounded_and_check_disables_hook():
    spec = importlib.util.spec_from_file_location("experiment", ROOT / "scripts/experiment_pr.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    document = {
        "id": "hook-test", "agent": "claude", "task": "t3",
        "purpose": "Review the bounded test-hook fixture.",
    }
    assert module.validate_definition(Path("hook-test.json"), document)["task"] == "t3"
    with pytest.raises(ValueError):
        module.validate_definition(Path("hook-test.json"), {**document, "repeat": 3})
    assert "--noconftest" in (ROOT / "tasks/t3/check.sh").read_text()
