#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
python3 -m pytest --noconftest -q tests 2>&1 | tail -5
