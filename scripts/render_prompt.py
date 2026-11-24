"""Render the task prompt: fixed preamble (plan-first, self-report) + task-specific body."""
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
preamble_path = pathlib.Path(
    "prompts/t4-preamble.md" if task_dir.name == "t4" else "prompts/preamble.md"
)
preamble = preamble_path.read_text()
body = (task_dir / "TASK.md").read_text()
print(preamble.rstrip() + "\n\n" + body.rstrip())
