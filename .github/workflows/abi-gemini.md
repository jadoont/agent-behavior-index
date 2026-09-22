---
name: ABI Gemini pilot
on:
  workflow_call:
    inputs:
      task:
        type: string
        required: true
engine: gemini
permissions:
  contents: read
timeout-minutes: 12
strict: true
env:
  ABI_ENGINE: gemini
imports:
  - shared/abi-pilot.md
---

{{#runtime-import shared/abi-prompt.md}}
