#!/usr/bin/env bash
# Test the packaged client with only the selected keyboard's Raw HID node visible.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT=$PWD
NODE=$(.venv-linux/bin/python - <<'PY'
import hidraw
matches = [d for d in hidraw.enumerate(0x4D58, 0x0103)
           if d['usage_page'] == 0xFF60 and d['usage'] == 0x61
           and d['serial_number'] == 'vial:f64c2b3c']
assert len(matches) == 1, matches
path = matches[0]['path']
print(path.decode() if isinstance(path, bytes) else path)
PY
)
# Concurrent readers can consume each other's replies. Leave them untouched.
if fuser "$NODE" >/dev/null 2>&1; then
    echo "Another process is using $NODE; close that client before read-only validation." >&2
    exit 1
fi
TESTDIR=$(mktemp -d /tmp/vial-astro-hardware.XXXXXX)
trap 'rm -rf "$TESTDIR"' EXIT
cp target/astro/Vial-Astro-0.7.5-x86_64.AppImage "$TESTDIR/"
mkdir -p "$TESTDIR/home" target/astro/hardware-validation
bwrap --ro-bind / / --dev /dev --dev-bind "$NODE" "$NODE" --proc /proc \
    --tmpfs "$ROOT" --tmpfs "$HOME/.local/share/uv" \
    --bind "$TESTDIR" "$TESTDIR" --chdir "$TESTDIR" \
    /usr/bin/env -i PATH=/usr/bin:/bin HOME="$TESTDIR/home" TMPDIR="$TESTDIR" \
    VIAL_ASTRO_READONLY_DIAGNOSTICS="$TESTDIR/capture" \
    ./Vial-Astro-0.7.5-x86_64.AppImage --appimage-extract-and-run \
    > target/astro/hardware-validation/packaged.log 2>&1
cp -a "$TESTDIR/capture/." target/astro/hardware-validation/
python3 - <<'PY'
import json
from pathlib import Path
folder = Path('target/astro/hardware-validation')
summary = json.loads((folder / 'summary.json').read_text())
records = [json.loads(line) for line in (folder / 'transactions.jsonl').read_text().splitlines()]
assert summary['reload']['complete']
assert summary['descriptor']['vendor_id'] == 0x4D58 and summary['descriptor']['product_id'] == 0x0103
assert not summary['errors'] and not summary['blocked_commands']
assert all(record['length'] == 32 and record['write_count'] == 33 for record in records)
# This specific keyboard advertises no strip synchronization masters.
assert not any(record['request'].startswith('fd3d0103') for record in records)
assert all(bytes.fromhex(record['response'])[2] == 0xAA
           for record in records if record['request'].startswith('fd'))
assert 'Failed to reload rgb param' not in (folder / 'reload-stdout.txt').read_text()
print('HARDWARE PASS: packaged client, {} reads, no transport errors or unsupported sync requests'.format(len(records)))
PY
cat target/astro/hardware-validation/packaged.log
