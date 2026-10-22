#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT=$PWD
mkdir -p target/astro/independent-test
TESTDIR=$(mktemp -d /tmp/vial-astro-test.XXXXXX)
trap 'rm -rf "$TESTDIR"' EXIT
cp target/astro/Vial-Astro-0.7.5-x86_64.AppImage "$TESTDIR/"
mkdir -p "$TESTDIR/home"
for PLATFORM in wayland xcb; do
    # Hide the entire source/venv and managed Python; expose a synthetic /dev
    # without keyboards, USB devices or /dev/input. No hardware can be opened.
    bwrap --ro-bind / / --dev /dev --dir /dev/bus/usb --proc /proc \
        --tmpfs "$ROOT" --tmpfs "$HOME/.local/share/uv" \
        --bind "$TESTDIR" "$TESTDIR" --chdir "$TESTDIR" \
        /usr/bin/env -i PATH=/usr/bin:/bin HOME="$TESTDIR/home" \
        TMPDIR="$TESTDIR" XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" DISPLAY="${DISPLAY:-}" \
        WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
        XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
        DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
        QT_QPA_PLATFORM="$PLATFORM" VIAL_ASTRO_SMOKE_TEST=1 \
        VIAL_ASTRO_SCREENSHOT="$TESTDIR/$PLATFORM.png" \
        ./Vial-Astro-0.7.5-x86_64.AppImage --appimage-extract-and-run \
        > "target/astro/independent-test/$PLATFORM.log" 2>&1
    cp "$TESTDIR/$PLATFORM.png" "target/astro/independent-test/"
    cat "target/astro/independent-test/$PLATFORM.log"
done
# Exercise the normal FUSE runtime and actual libusb initialization separately;
# libusb cannot initialize against the synthetic device tree above.
python3 - <<'PY'
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix='vial-astro-native.') as folder:
    binary = Path(folder) / 'Vial-Astro.AppImage'
    shutil.copy2('target/astro/Vial-Astro-0.7.5-x86_64.AppImage', binary)
    env = {k: os.environ[k] for k in ['XDG_RUNTIME_DIR', 'WAYLAND_DISPLAY', 'DISPLAY', 'XAUTHORITY'] if k in os.environ}
    env.update(PATH='/usr/bin:/bin', HOME=folder, QT_QPA_PLATFORM='wayland',
               VIAL_ASTRO_SMOKE_TEST='1', VIAL_ASTRO_TEST_USB_INIT='1')
    result = subprocess.run([str(binary)], cwd=folder, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    Path('target/astro/independent-test/native-runtime.log').write_bytes(result.stdout)
    print(result.stdout.decode(), end='')
    if result.returncode:
        raise SystemExit(result.returncode)
PY
