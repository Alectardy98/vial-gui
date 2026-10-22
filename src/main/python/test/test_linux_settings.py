"""The Linux launcher keeps Astro preferences without isolating Qt session config."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
                                reason='Linux native launcher/discovery regression')

ROOT = Path(__file__).resolve().parents[4]
HOOK = ROOT / 'util/native-linux/runtime_hook.py'


@pytest.mark.parametrize('custom_config', [False, True])
def test_settings_path_and_persistence(tmp_path, custom_config):
    env = os.environ.copy()
    for key in ['VIAL_ASTRO_SMOKE_TEST', 'VIAL_ASTRO_READONLY_DIAGNOSTICS', 'XDG_CONFIG_HOME']:
        env.pop(key, None)
    env['HOME'] = str(tmp_path / 'home')
    config = tmp_path / 'custom-config' if custom_config else Path(env['HOME']) / '.config'
    if custom_config:
        env['XDG_CONFIG_HOME'] = str(config)
    astro = config / 'vial-astro/Vial/Vial.conf'
    official = config / 'Vial/Vial.conf'
    for path, theme in [(astro, 'ExistingAstro'), (official, 'OfficialUnchanged')]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('[General]\ntheme={}\n'.format(theme))
    original_official = official.read_bytes()
    program = '''
import json, os, runpy, sys
from PyQt5.QtCore import QSettings, QStandardPaths
before = os.environ.get('XDG_CONFIG_HOME')
runpy.run_path(sys.argv[1])
settings = QSettings('Vial', 'Vial')
result = dict(file=settings.fileName(), theme=settings.value('theme'),
              persisted=settings.value('persistence_probe'),
              config=QStandardPaths.writableLocation(QStandardPaths.ConfigLocation),
              env_unchanged=before == os.environ.get('XDG_CONFIG_HOME'))
if sys.argv[2] == 'write':
    settings.setValue('persistence_probe', 'saved-across-processes')
    settings.sync()
    assert settings.status() == QSettings.NoError
print(json.dumps(result))
'''
    for operation in ['write', 'read']:
        result = subprocess.run([sys.executable, '-c', program, str(HOOK), operation],
                                env=env, text=True, capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert Path(data['file']) == astro
        assert Path(data['config']) == config
        assert data['env_unchanged']
        assert data['theme'] == 'ExistingAstro'
        assert data['persisted'] == (None if operation == 'write' else 'saved-across-processes')
    assert official.read_bytes() == original_official
