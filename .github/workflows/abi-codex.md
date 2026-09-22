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
max-daily-ai-credits: 100
safe-outputs:
  report-failed-jobs: false
  report-failure-as-issue: false
  missing-tool: false
  missing-data: false
  report-incomplete: false
  scripts:
    pilot-complete:
      description: Acknowledge completion without publishing.
      script: |
        return async function () { return { success: true }; };
model: gpt-5.3-codex
env:
  ABI_ENGINE: codex
imports:
  - shared/abi-pilot.md
---

{{#runtime-import shared/abi-prompt.md}}
