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
env:
  ABI_ENGINE: gemini
imports:
  - shared/abi-pilot.md
---

{{#runtime-import shared/abi-prompt.md}}
