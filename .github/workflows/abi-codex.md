---
name: ABI Codex pilot
on:
  workflow_call:
    inputs:
      task:
        type: string
        required: true
engine: codex
permissions:
  contents: read
timeout-minutes: 12
strict: true
model: gpt-5.3-codex
env:
  ABI_ENGINE: codex
imports:
  - shared/abi-pilot.md
---

{{#runtime-import shared/abi-prompt.md}}
