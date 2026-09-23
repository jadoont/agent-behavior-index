import importlib.util
import json
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


def test_failed_activation_still_posts_an_honest_receipt(tmp_path, monkeypatch):
    for key, value in {
        "GITHUB_REPOSITORY": "example/repo", "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1", "ABI_PR": "4", "ABI_TASK": "c0",
        "ABI_EXPERIMENT": "test-c0", "ABI_HEAD_SHA": "a" * 40,
        "ABI_JOB_RESULT": "failure", "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }.items():
        monkeypatch.setenv(key, value)

    def fake_gh(*args, **kwargs):
        endpoint = args[1]
        if "/artifacts?" in endpoint:
            return json.dumps({"artifacts": []})
        if "/jobs?" in endpoint:
            return json.dumps({"jobs": [{
                "name": "experiment / agent", "id": 5,
                "status": "completed", "conclusion": "skipped",
            }]})
        if "/comments" in endpoint:
            return "[[]]"
        raise AssertionError(f"Unexpected API call: {args}")

    posted = []
    monkeypatch.setattr(module, "gh", fake_gh)
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw: posted.append(kw["input"]))
    module.receipt()
    body = json.loads(posted[0])["body"]
    assert "Workflow: **failure**" in body
    assert "NOT VERIFIED / FAIL" in body
    assert "Exact Garnet profile not verified" in body
