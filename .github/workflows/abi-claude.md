---
name: ABI Claude pilot
on:
  workflow_call:
    inputs:
      task:
        type: string
        required: true
engine: claude
permissions:
  contents: read
timeout-minutes: 12
strict: true
model: claude-sonnet-4-6
env:
  ABI_ENGINE: claude
imports:
  - shared/abi-pilot.md
---

{{#runtime-import shared/abi-prompt.md}}
