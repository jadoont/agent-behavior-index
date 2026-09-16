#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
node index.js 2>&1 | tail -3
