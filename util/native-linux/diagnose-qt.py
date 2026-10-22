"""Device-free origin/impact checks for the fbs QSocketNotifier warning."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

root=Path(__file__).resolve().parents[2]
os.chdir(root)
sys.path.insert(0,str(root/'src/main/python'))
from PyQt5.QtCore import qInstallMessageHandler, QTimer, QThread
messages=[]
def handler(kind,context,message):
    item={'kind':int(kind),'message':message,'stack':traceback.format_stack()}
    messages.append(item)
    print('QT_MESSAGE '+json.dumps(item),flush=True)
qInstallMessageHandler(handler)
parser=argparse.ArgumentParser()
parser.add_argument('--mode',choices=['fbs','qt'],default='fbs')
args=parser.parse_args()
if args.mode=='fbs':
    print('STAGE before main import',flush=True)
    from main import VialApplicationContext
    print('STAGE before context',flush=True)
    context=VialApplicationContext()
    app=context.app
else:
    from PyQt5.QtWidgets import QApplication
    app=QApplication([])
    signal.signal(signal.SIGINT,lambda *_:app.exit(130))
print('STAGE event loop ready',flush=True)
QTimer.singleShot(2500, lambda:app.exit(99))
start=time.monotonic()
result=app.exec_()
print('RESULT '+json.dumps({'mode':args.mode,'elapsed':time.monotonic()-start,'exit_code':result,'messages':messages}),flush=True)
