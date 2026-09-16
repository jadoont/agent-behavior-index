"""Render the task prompt: fixed preamble (plan-first, self-report) + task-specific body."""
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
preamble = pathlib.Path("prompts/preamble.md").read_text()
body = (task_dir / "TASK.md").read_text()
print(preamble.rstrip() + "\n\n" + body.rstrip())
