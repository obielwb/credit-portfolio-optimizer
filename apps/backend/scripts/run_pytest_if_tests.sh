#!/usr/bin/env bash
set -euo pipefail

set +e
pytest --collect-only -q >/dev/null
collect_exit_code=$?
set -e

if [[ $collect_exit_code -eq 5 ]]; then
  echo 'pytest skipped: no tests found'
  exit 0
fi

if [[ $collect_exit_code -ne 0 ]]; then
  exit "$collect_exit_code"
fi

pytest
