---
permissions:
  contents: read
max-turns: 20
max-ai-credits: 50
network:
  allowed:
    - defaults
    - github.com
    - api.github.com
    - "*.githubusercontent.com"
    - registry.npmjs.org
    - pypi.org
    - files.pythonhosted.org
    - api.anthropic.com
    - api.openai.com
    - generativelanguage.googleapis.com
    - api.garnet.ai
sandbox:
  agent:
    runtime: docker-sudo-iptables
tools:
  bash: ["*"]
  edit:
safe-outputs:
  noop:
  report-failure-as-issue: false
  missing-data:
    create-issue: false
  scripts:
    pilot-complete:
      description: Acknowledge pilot completion without publishing anything.
      script: |
        return async function () {
          return { success: true };
        };
steps:
  - name: Validate pilot task and prepare tools
    env:
      ABI_TASK: ${{ inputs.task }}
    run: |
      case "$ABI_TASK" in c0|t2) ;; *) exit 2 ;; esac
      python3 -m pip install pytest
      mkdir -p /tmp/abi-evidence
      cp scripts/ghaw_evidence.py /tmp/abi-evidence-check.py
      python3 scripts/render_prompt.py "tasks/$ABI_TASK" > /tmp/abi-evidence/task-prompt.txt
  - name: Require verified Garnet organization for Codex
    if: env.ABI_ENGINE == 'codex'
    env:
      ABI_OPENAI_ORG_VERIFIED: ${{ vars.ABI_OPENAI_ORG_VERIFIED }}
    run: |
      if [ "$ABI_OPENAI_ORG_VERIFIED" != "garnet" ]; then
        echo "::error::Codex blocked: replace OPENAI_API_KEY with a verified Garnet abi-sprint project key, then set ABI_OPENAI_ORG_VERIFIED=garnet."
        exit 1
      fi
pre-agent-steps:
  - name: Garnet Runtime Review
    id: garnet
    uses: garnet-org/action@3d47f4a9004f7356c980a0e8d420ef5984750e3c
    with:
      api_token: ${{ secrets.GARNET_API_TOKEN }}
      debug: true
post-steps:
  - name: Independently check task and collect redacted evidence
    if: always()
    env:
      ABI_TASK: ${{ inputs.task }}
      ABI_PRIOR_STATUS: ${{ job.status }}
      ABI_REPORT_URL: ${{ steps.garnet.outputs.report_url }}
    run: |
      sudo cp /var/log/jibril.out /tmp/abi-jibril.out 2>/dev/null || true
      sudo chown "$(id -u)" /tmp/abi-jibril.out 2>/dev/null || true
      python3 /tmp/abi-evidence-check.py
  - name: Upload pilot evidence
    if: always()
    uses: actions/upload-artifact@v7.0.1
    with:
      name: abi-${{ env.ABI_ENGINE }}-${{ inputs.task }}-${{ github.run_id }}-${{ github.run_attempt }}
      path: /tmp/abi-evidence
      retention-days: 7
      if-no-files-found: error
  - name: Enforce task and evidence gate
    if: always()
    run: |
      python3 -c 'import json; r=json.load(open("/tmp/abi-evidence/result.json")); assert r["pilot_pass"], "Pilot did not pass; see result.json and workflow summary"'
---
