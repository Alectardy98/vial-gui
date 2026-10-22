#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT=$PWD
UV=${UV:-$ROOT/.build-tools/uv}
APPIMAGETOOL=${APPIMAGETOOL:-/usr/bin/appimagetool}
test -x "$UV" || { echo 'Provide UV=/path/to/uv (or install uv in .build-tools).'; exit 1; }
test -x "$APPIMAGETOOL"
RUNTIME=$ROOT/.build-tools/runtime-x86_64
mkdir -p "$ROOT/.build-tools"
if [[ ! -f "$RUNTIME" ]]; then
    curl -fL https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64 -o "$RUNTIME"
fi
printf '%s  %s\n' 617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46 "$RUNTIME" | sha256sum -c -
"$UV" venv --python 3.11.17 --allow-existing .venv-linux
PY=$ROOT/.venv-linux/bin/python
"$UV" pip install --python "$PY" -r util/native-linux/requirements.lock
# fbs requires obsolete PyInstaller pins; retain only its unchanged runtime API.
"$UV" pip install --python "$PY" --no-deps fbs==0.9.0 ./simpleeval.zip
"$UV" pip install --python "$PY" --no-build-isolation 'git+https://github.com/vial-kb/cython-hidapi@fa31fd46e709ac4adba80bd516b1290dd56f43e9#egg=hidapi'
mkdir -p target/astro
"$PY" - <<'PY'
import json
from pathlib import Path
settings = json.loads(Path('src/build/settings/base.json').read_text())
settings['app_name'] = 'Vial Astro'
Path('target/astro/build-settings.json').write_text(json.dumps(settings))
PY
.venv-linux/bin/pyinstaller --noconfirm --clean --distpath target/astro/dist --workpath target/astro/work util/native-linux/VialAstro.spec > target/astro/pyinstaller.log 2>&1
APPDIR=$ROOT/target/astro/VialAstro.AppDir
"$PY" -c 'import shutil, sys; shutil.rmtree(sys.argv[1], ignore_errors=True)' "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a target/astro/dist/VialAstro/. "$APPDIR/usr/bin/"
install -m755 util/native-linux/AppRun "$APPDIR/AppRun"
cp util/native-linux/vial-astro.desktop "$APPDIR/"
cp src/main/icons/linux/256.png "$APPDIR/vial-astro.png"
cp COPYING "$APPDIR/COPYING"
cp util/native-linux/README.md "$APPDIR/BUILD-README.md"
cp util/native-linux/CHANGES-LINUX.md "$APPDIR/CHANGES-LINUX.md"
cp util/native-linux/STARTUP-FIXES.md "$APPDIR/STARTUP-FIXES.md"
cp util/native-linux/LOCALIZATION.md "$APPDIR/LOCALIZATION.md"
cp util/native-linux/RGB-STRIP-FIX.md "$APPDIR/RGB-STRIP-FIX.md"
cp util/native-linux/RGB-ALL-PREVIEWS.md "$APPDIR/RGB-ALL-PREVIEWS.md"
cp util/native-linux/LOCALIZATION-STRINGS.json "$APPDIR/LOCALIZATION-STRINGS.json"
git diff --binary HEAD -- src > "$APPDIR/SOURCE_CHANGES.patch"
"$PY" - "$APPDIR/SOURCE_MANIFEST.sha256" <<'PYMANIFEST'
import hashlib
from pathlib import Path
import sys
files = [p for p in Path('src').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
files += [p for p in Path('util/native-linux').iterdir() if p.is_file() and p.suffix not in {'.md', '.pyc'}]
files += [Path('COPYING'), Path('requirements.txt'), Path('simpleeval.zip')]
Path(sys.argv[1]).write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p) + '\n' for p in sorted(files)))
PYMANIFEST
cp util/native-linux/requirements.lock "$APPDIR/requirements.lock"
git rev-parse HEAD > "$APPDIR/SOURCE_COMMIT"
# Build beside the destination and rename atomically. A running AppImage may
# hold the old inode open; never stop it or truncate its mounted backing file.
IMAGE=$ROOT/target/astro/Vial-Astro-0.7.5-x86_64.AppImage
STAGED_IMAGE=$(mktemp "$ROOT/target/astro/.Vial-Astro.XXXXXX.AppImage")
trap 'rm -f "$STAGED_IMAGE"' EXIT
ARCH=x86_64 "$APPIMAGETOOL" --runtime-file "$RUNTIME" "$APPDIR" "$STAGED_IMAGE"
mv -f -- "$STAGED_IMAGE" "$IMAGE"
cd target/astro
sha256sum Vial-Astro-0.7.5-x86_64.AppImage > Vial-Astro-0.7.5-x86_64.AppImage.sha256
