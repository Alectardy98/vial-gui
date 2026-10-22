#!/usr/bin/env bash
# All automated tests use virtual devices; physical devices are inaccessible.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT=$PWD
mkdir -p target/astro/automated-tests
bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
    --bind "$ROOT/target/astro/automated-tests" "$ROOT/target/astro/automated-tests" \
    --chdir "$ROOT" /usr/bin/env QT_QPA_PLATFORM=offscreen \
    XDG_CONFIG_HOME="$ROOT/target/astro/automated-tests/config" \
    XDG_DATA_HOME="$ROOT/target/astro/automated-tests/data" \
    XDG_CACHE_HOME="$ROOT/target/astro/automated-tests/cache" \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/src/main/python" \
    "$ROOT/.venv-linux/bin/python" -m pytest -q \
    -o cache_dir=target/astro/automated-tests/pytest-cache \
    --junitxml=target/astro/automated-tests/results.xml src/main/python/test "$@"
