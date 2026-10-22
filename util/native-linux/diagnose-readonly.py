#!/usr/bin/env python3
"""Read-only diagnostic harness. Every transmitted payload passes an allowlist.
Never call setters, unlock/lock, reset, calibration, firmware or file operations.
"""
import argparse
import contextlib
import hashlib
import io
import json
import lzma
from pathlib import Path
import statistics
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = Path(sys._MEIPASS)
else:
    sys.path.insert(0, str(ROOT / 'src/main/python'))
    RESOURCE_DIR = ROOT / 'src/main/resources/base'
import hidraw

# Explicit getter opcodes read from this fork's protocol implementation.
AMK_GET = {0,1,3,5,7,9,11,13,15,17,19,21,23,25,27,28,29,31,33,
           35,36,43,44,45,47,49,51,52,54,56,58,60,61,63,65,66,67,69,71}
# Keep optional/possibly stateful GETs outside our experiments unless needed;
# file, firmware, clock and streaming-state requests are excluded below.
AMK_GET -= {35,36,54,63}

def allowed(msg):
    if not msg or len(msg) > 32:
        return False
    if msg[0] == 0xFD:
        return len(msg) >= 2 and msg[1] in AMK_GET
    if msg[0] == 0xFE:
        if len(msg) < 2:
            return False
        if msg[1] == 0x0D:
            return len(msg) >= 3 and msg[2] in {0,1,3,5,7}
        return msg[1] in {0,1,2,3,5,9,10}
    if msg[0] == 2:
        return len(msg) >= 2 and msg[1] == 2  # layout options only
    return msg[0] in {1,4,8,12,13,14,17,18}

class ReadOnlyDevice:
    def __init__(self, desc, output):
        self.desc, self.output = desc, output
        self.output.mkdir(parents=True, exist_ok=True)
        self.records = []
        self.blocked = []
        self.dev = hidraw.device()
        self.dev.open_path(desc['path'])

    def exchange(self, msg, retries=1):
        msg = bytes(msg)
        if not allowed(msg):
            self.blocked.append(msg.hex())
            raise RuntimeError('Read-only guard rejected command ' + msg.hex())
        wire = b'\0' + msg.ljust(32, b'\0')
        start = time.perf_counter()
        record = {'request': msg.hex(), 'wire_report': wire.hex()}
        try:
            count = self.dev.write(wire)
            record['write_count'] = count
            if count != 33:
                raise RuntimeError('Short HID output report: ' + str(count))
            response = bytes(self.dev.read(32, timeout_ms=1000))
            record['response'] = response.hex()
            record['length'] = len(response)
            if len(response) != 32:
                raise RuntimeError('Short/timed out input report: ' + str(len(response)))
            return response
        except Exception as exc:
            record['error'] = repr(exc)
            raise
        finally:
            record['elapsed_ms'] = (time.perf_counter()-start)*1000
            self.records.append(record)
            with (self.output / 'transactions.jsonl').open('a') as log:
                log.write(json.dumps(record)+'\n')
            time.sleep(0.005)

    def send(self, dev, msg, retries=1):
        assert dev is self.dev
        # No automatic retries: preserve first-response evidence.
        return self.exchange(msg)

    def close(self):
        self.dev.close()


def clean(obj):
    if isinstance(obj, dict): return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [clean(v) for v in obj]
    if isinstance(obj, set): return sorted(clean(v) for v in obj)
    if hasattr(obj, '__dict__'): return clean(vars(obj))
    return obj


def serializable(obj):
    if isinstance(obj, bytes): return obj.hex()
    if isinstance(obj, Path): return str(obj)
    if isinstance(obj, set): return sorted(obj)
    if hasattr(obj, '__dict__'): return obj.__dict__
    return str(obj)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--full-reload', action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / 'transactions.jsonl').exists():
        raise SystemExit('Choose a fresh output directory to keep captures distinct')
    descs=hidraw.enumerate(0x4D58,0x0103)
    (args.output/'hid-enumeration.json').write_text(json.dumps(descs,default=serializable,indent=2))
    matches=[d for d in descs if d['usage_page']==0xFF60 and d['usage']==0x61]
    assert len(matches)==1, matches
    desc=matches[0]
    assert desc['serial_number']=='vial:f64c2b3c'
    diag=ReadOnlyDevice(desc,args.output)
    summary={'descriptor':desc}
    try:
        via=diag.exchange(b'\x01')
        identity=diag.exchange(b'\xfe\x00')
        summary['via_protocol']=struct.unpack('>H',via[1:3])[0]
        summary['vial_protocol'],uid=struct.unpack('<IQ',identity[:12])
        summary['keyboard_id']=f'{uid:016X}'
        size=struct.unpack('<I',diag.exchange(b'\xfe\x01')[:4])[0]
        assert 0<size<1024*1024, size
        compressed=b''.join(diag.exchange(struct.pack('<BBI',0xFE,2,page)) for page in range((size+31)//32))[:size]
        definition=json.loads(lzma.decompress(compressed))
        (args.output/'keyboard-definition.json').write_text(json.dumps(definition,indent=2,ensure_ascii=False))
        summary['definition_size']=size
        summary['definition_sha256']=hashlib.sha256(compressed).hexdigest()
        summary['definition_metadata']={k:v for k,v in definition.items() if k!='layouts'}
        summary['layers']=diag.exchange(b'\x11')[1]
        summary['nkro_response']=diag.exchange(b'\xfd\x0d').hex()
        strips=[]
        for feature in definition.get('amkFeature',[]):
            if isinstance(feature,dict) and 'rgb_strip' in feature:
                strips=feature['rgb_strip']['strips']
        summary['rgb_samples']=[]
        from amk.protocol import ProtocolAmk
        rgb_protocol = ProtocolAmk()
        rgb_protocol.amk_rgb_strip = {'strips': strips}
        # Request only parameters the GUI normally reads, with declared indexes.
        for iteration in range(4):
            for index in range(len(strips)):
                params = (0,2,3) if rgb_protocol.rgb_strip_supports_sync(index) else (0,2)
                for param in params:
                    request=bytes([0xFD,61,1,param,index])
                    response=diag.exchange(request)
                    summary['rgb_samples'].append({'iteration':iteration,'strip':index,'param':param,'request':request.hex(),'response':response.hex(),'status':response[2]})
            diag.exchange(b'\x01')  # independent read after RGB responses
            diag.exchange(b'\xfd\x0d')
        if args.full_reload:
            from editor.qmk_settings import QmkSettings
            QmkSettings.initialize(type('ResourceContext', (), {'get_resource': lambda self, name: str(RESOURCE_DIR / name)})())
            from protocol.keyboard_comm import Keyboard
            keyboard=Keyboard(diag.dev,usb_send=diag.send)
            captured=io.StringIO()
            with contextlib.redirect_stdout(captured):
                keyboard.reload()
            (args.output/'reload-stdout.txt').write_text(captured.getvalue())
            summary['reload']={'complete':True,'attributes':{k:v for k,v in vars(keyboard).items() if k not in {'dev','usb_send','definition','keys','encoders'}}}
        summary['blocked_commands']=diag.blocked
    finally:
        diag.close()
        summary['transactions']=len(diag.records)
        summary['errors']=[r for r in diag.records if 'error' in r]
        times=[r['elapsed_ms'] for r in diag.records]
        summary['timing_ms']={'min':min(times),'median':statistics.median(times),'max':max(times)} if times else {}
        (args.output/'summary.json').write_text(json.dumps(clean(summary),default=serializable,indent=2,ensure_ascii=False))
    print(json.dumps({k:v for k,v in summary.items() if k not in {'definition_metadata','reload','rgb_samples','descriptor'}},default=serializable,indent=2))

if __name__=='__main__': main()
