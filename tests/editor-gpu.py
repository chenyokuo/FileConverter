"""Opt-in shipping editor → existing GPU/CPU encoder integration on this host."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time
from test_engine import Client

ROOT = Path(__file__).resolve().parents[1]
candidate = Path(sys.argv[1]).resolve()
os.environ['FILE_CONVERTER_TEST_FROZEN'] = str(candidate / 'binaries/FileConverterEngine/FileConverterEngine.exe')
os.environ['FILE_CONVERTER_TEST_ENGINES'] = str(candidate / 'engines')
os.environ['PATH'] = os.environ['SystemRoot'] + r'\System32;' + os.environ['SystemRoot']
checks = []
with tempfile.TemporaryDirectory(dir=ROOT / '.tools', prefix='editor-gpu-') as scratch:
    client = Client(Path(scratch) / 'data')
    try:
        deadline = time.monotonic() + 30
        while any(d.get('pending') for d in client.call('hardware')) and time.monotonic() < deadline:
            time.sleep(.1)
        capabilities = client.call('hardware')
        for device in capabilities:
            hardware = device['id']
            project = {'type':'fcvideo','version':1,'width':320,'height':240,'fps':20,
                'clips':[{'id':'qa', 'source':str(ROOT / '.tools/editor-ui/red.mp4'), 'track':'V1','in':0,'out':1,'at':0}],
                'export':{'hardware':hardware,'videoCodec':'h264','qualityPreset':'fast'}}
            job = client.call('editor', {'action':'enqueue','type':'fcvideo','project':project,'format':'mp4','outputDir':str(Path(scratch)/'out')})
            result = client.wait([job['id']], timeout=90)[0]
            assert result['status'] == 'completed', result.get('error')
            stats = result['stats']
            assert stats.get('encoder')
            if not device['available']:
                assert stats['encoder'] == 'libx264' and stats.get('hardwareFallback'), stats
            metadata = json.loads(subprocess.check_output([str(candidate/'engines/ffmpeg/ffprobe.exe'),'-v','error','-show_format','-of','json',result['outputs'][0]],text=True))
            duration = float(metadata['format']['duration'])
            assert abs(duration-1)<.1
            checks.append({'requested':hardware,'detectedAvailable':device['available'], 'actualEncoder':stats['encoder'],
                'fallbackReported':bool(stats.get('hardwareFallback')),'duration':duration})
    finally:
        client.close()
report = {'frozenSidecar':True,'checks':checks,'note':'CPU composition, existing final encode/fallback. Unavailable hardware is not physical GPU certification.'}
(ROOT/'test-results/multimedia-editor-gpu.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
