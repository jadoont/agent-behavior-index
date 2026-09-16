#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
python3 -c "
import report
print('has summarize:', hasattr(report, 'summarize'))
"
python3 -m pytest -q 2>&1 | tail -5
