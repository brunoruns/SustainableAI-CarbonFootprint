#!/usr/bin/env bash
# Run de volledige test-harness: lint, type check en tests.
# Exit code 0 = alles geslaagd, anders faalt de harness.
set -euo pipefail

cd "$(dirname "$0")/.."

fail=0

echo "== Lint (ruff) =="
if command -v ruff >/dev/null 2>&1; then
    ruff check . || fail=1
else
    echo "ruff niet beschikbaar; stap overgeslagen"
fi

echo "== Type check (mypy) =="
if command -v mypy >/dev/null 2>&1; then
    mypy . || fail=1
else
    echo "mypy niet beschikbaar; stap overgeslagen"
fi

echo "== Tests (pytest) =="
if command -v pytest >/dev/null 2>&1; then
    pytest tests/ || fail=1
else
    echo "pytest niet beschikbaar; stap overgeslagen"
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "== Harness geslaagd =="
else
    echo "== Harness gefaald =="
fi
exit "$fail"
