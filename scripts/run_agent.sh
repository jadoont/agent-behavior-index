#!/usr/bin/env bash
# Run one agent headlessly on one task directory. Writes transcript + prompt into $out.
set -uo pipefail
agent="$1"; task_dir="$2"; out="$3"
mkdir -p "$out"
prompt="$(python3 scripts/render_prompt.py "$task_dir")"
printf '%s\n' "$prompt" > "$out/prompt.txt"
cd "$task_dir"
case "$agent" in
  claude)
    claude -p "$prompt" --output-format stream-json --verbose --dangerously-skip-permissions \
      > "../../$out/transcript.jsonl" 2> "../../$out/stderr.txt" ;;
  codex)
    codex exec --full-auto --json "$prompt" \
      > "../../$out/transcript.jsonl" 2> "../../$out/stderr.txt" ;;
  grok)
    echo "TODO: Grok Build headless invocation" > "../../$out/stderr.txt"; exit 1 ;;
  none)
    echo "no agent; running task check only" > "../../$out/transcript.jsonl" ;;
esac
echo "exit=$?" > "../../$out/agent_exit.txt"
git -C . diff > "../../$out/agent.diff" 2>/dev/null || true
exit 0
