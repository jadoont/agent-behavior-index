import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("experiment_pr", ROOT / "scripts/experiment_pr.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def definition(**updates):
    return {"id": "test-c0", "agent": "claude", "task": "c0",
            "purpose": "Test the bounded PR path.", **updates}


def test_valid_definition():
    assert module.validate_definition(Path("test-c0.json"), definition())["task"] == "c0"


@pytest.mark.parametrize("updates", [
    {"agent": "codex"}, {"task": "arbitrary-shell"}, {"id": "wrong"},
    {"purpose": "x"}, {"model": "premium"}, {"repeat": 100},
])
def test_unbounded_or_unverified_definitions_rejected(updates):
    with pytest.raises(ValueError):
        module.validate_definition(Path("test-c0.json"), definition(**updates))


def test_paid_pr_lane_is_opt_in_and_not_fork_or_bot_triggered():
    text = (ROOT / ".github/workflows/experiment-pr.yml").read_text()
    assert "pull_request_target" not in text
    assert "head.repo.full_name == github.repository" in text
    assert "user.type != 'Bot'" in text
    assert "author_association" in text
    assert "'abi:run'" in text
    assert "secrets: inherit" not in text
    assert "OPENAI_API_KEY" not in text
    assert "GEMINI_API_KEY" not in text
