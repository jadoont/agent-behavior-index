"""Fail CI if recompilation drops ABI's cost or tokenless-capture controls."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "claude": "anthropic/claude-sonnet-4-6",
    "codex": "openai/gpt-5.6-terra",
    "gemini": "google/gemini-3.8-flash",
}


def configs(text):
    return [
        json.loads(match[1])
        for match in re.finditer(r"printf '%s\\n' '(\{[^\n]+\})' >", text)
        if '"apiProxy"' in match[1]
    ]


def test_compiled_model_policy_covers_agent_and_detection():
    allowlists = []
    for engine, model in MODELS.items():
        text = (ROOT / ".github/workflows" / f"abi-{engine}.lock.yml").read_text()
        policies = configs(text)
        assert len(policies) == 2
        for config, budget in zip(policies, (50, 50)):
            proxy = config["apiProxy"]
            assert proxy["allowedModels"] == [model.split("/", 1)[1], model]
            assert proxy["modelFallback"] == {"enabled": False}
            assert proxy["enableTokenSteering"] is False
            assert proxy["maxAiCredits"] == budget
        allowlists.append(policies[0]["network"]["allowDomains"])
        assert "GARNET_API_TOKEN" not in text
        assert "249153cfd535f8a08c328c1ef71eeb4b1b9ac096" in text
        assert "jibril_version: v2.17.0" in text
        assert "--exclude-env ACTIONS_ID_TOKEN_REQUEST_TOKEN" in text
        assert "--exclude-env ACTIONS_ID_TOKEN_REQUEST_URL" in text
        assert 'GH_AW_DETECTION_CONTINUE_ON_ERROR: "false"' in text
    assert allowlists[0] == allowlists[1] == allowlists[2]
    assert len(allowlists[0]) == 45


def test_dependabot_uses_ordinary_pr_workflow_without_provider_secrets():
    text = (ROOT / ".github/workflows/test.yml").read_text()
    assert "pull_request:" in text
    assert "pull_request_target:" not in text
    assert "id-token: write" in text
    assert "secrets." not in text
    assert "pull-requests: write" not in text
    assert "persist-credentials: false" in text
