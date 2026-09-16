#!/usr/bin/env bash
# Task success criterion for C0. Exits non-zero on failure but the workflow records either way.
set -uo pipefail
cd "$(dirname "$0")"
python3 -m pytest -q tests 2>&1 | tail -5
