#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 - "$repo_root" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
task_root = root / "tasks" / "t4"
manifest = json.loads((root / "analysis" / "t4_key.json").read_text())
expected = manifest["sha256"]
actual = {
    path.relative_to(task_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (task_root / "src").rglob("*")
    if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
}
problems = []
for path in sorted(set(expected) | set(actual)):
    if path not in expected:
        problems.append(f"unexpected source file: {path}")
    elif path not in actual:
        problems.append(f"missing source file: {path}")
    elif actual[path] != expected[path]:
        problems.append(f"source changed: {path}")
if problems:
    print("\n".join(problems), file=sys.stderr)
    raise SystemExit(1)
print(f"PASS: {len(expected)} source files match analysis/t4_key.json")
PY
