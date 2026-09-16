#!/usr/bin/env bash
# Install the headless CLI for one agent. Deliberately a separate workflow step so
# its egress (npm registry) is attributed to setup, not to the agent workload.
set -euo pipefail
agent="$1"
case "$agent" in
  claude) npm install -g @anthropic-ai/claude-code ;;
  codex)  npm install -g @openai/codex ;;
  grok)   echo "TODO: Grok Build CLI install command (verify with xAI docs)"; exit 1 ;;
  none)   echo "no agent" ;;
  *) echo "unknown agent: $agent" >&2; exit 2 ;;
esac
