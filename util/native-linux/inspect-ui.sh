#!/usr/bin/env bash
# Render recorded and synthetic fixtures; physical HID/input/USB inaccessible.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT=$PWD
PLATFORM=${1:-wayland}
mkdir -p target/astro/localization/visual
OUTPUT=$ROOT/target/astro/localization/visual/$PLATFORM
mkdir -p "$OUTPUT"
bwrap --ro-bind / / --dev /dev --dir /dev/bus/usb --proc /proc --tmpfs /tmp \
    --bind "$OUTPUT" "$OUTPUT" --chdir "$ROOT" \
    /usr/bin/env QT_QPA_PLATFORM="$PLATFORM" VIAL_ASTRO_OFFLINE_UI=1 \
    XDG_CONFIG_HOME=/tmp/astro-ui/config XDG_DATA_HOME=/tmp/astro-ui/data \
    XDG_CACHE_HOME=/tmp/astro-ui/cache PYTHONDONTWRITEBYTECODE=1 \
    "$ROOT/.venv-linux/bin/python" util/native-linux/inspect-ui.py \
    --responses target/astro/hardware-validation/transactions.jsonl --output "$OUTPUT"
