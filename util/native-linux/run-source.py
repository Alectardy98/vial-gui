"""Run the unchanged custom entry point in a separate Vial Astro profile."""
import os
import runpy
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
os.chdir(root)
sys.path.insert(0, str(root / 'src/main/python'))
runpy.run_path(str(root / 'util/native-linux/runtime_hook.py'))
runpy.run_path(str(root / 'src/main/python/main.py'), run_name='__main__')
