#!/usr/bin/env python3
"""Compile with gh-aw, then close v0.88.8's detection model-policy omission.

The compiler copies the detection engine/model but omits models.allowed and
sandbox model controls from the detection AWF config. Patch only JSON config
literals, without changing generated workflow structure or source hashes.
Re-run this wrapper whenever any pilot Markdown changes.
"""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "claude": "anthropic/claude-sonnet-4-6",
    "codex": "openai/gpt-5.6-terra",
    "gemini": "google/gemini-3.8-flash",
}
subprocess.run(
    ["gh", "aw", "compile", *("abi-" + e for e in MODELS),
     "--no-check-update", "--validate", "--approve"],
    cwd=ROOT, check=True,
)
pattern = re.compile(r"(printf '%s\\n' ')(\{[^\n]+\})(' >)")
for engine, model in MODELS.items():
    path = ROOT / ".github/workflows" / f"abi-{engine}.lock.yml"
    count = [0]

    def enforce(match):
        config = json.loads(match[2])
        if "apiProxy" not in config:
            return match[0]
        proxy = config["apiProxy"]
        # Native provider requests use bare IDs; the canonical form is retained
        # for proxy versions that normalize names before applying the policy.
        proxy["allowedModels"] = [model.split("/", 1)[1], model]
        proxy["modelFallback"] = {"enabled": False}
        proxy["enableTokenSteering"] = False
        assert proxy["maxAiCredits"] == 50
        count[0] += 1
        return match[1] + json.dumps(config, separators=(",", ":")) + match[3]

    text = pattern.sub(enforce, path.read_text())
    assert count[0] == 2, f"{engine}: expected agent and detection configs"
    assert "GARNET_API_TOKEN" not in text
    assert "249153cfd535f8a08c328c1ef71eeb4b1b9ac096" in text
    path.write_text(text)
    print(f"{engine}: exact model enforced for agent and detector: {model}")
