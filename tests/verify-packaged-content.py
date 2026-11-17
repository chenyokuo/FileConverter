"""Inspect actual editor/core outputs produced by test-packaged.ps1, not job labels."""
from pathlib import Path
import json
import subprocess
import sys
from PIL import Image
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
candidate = Path(sys.argv[1]).resolve()
checks = []
for label in sys.argv[2:]:
    report = json.loads((ROOT / f'test-results/{label}-editors.json').read_text())
    movie, png, webp = map(Path, report['outputs'])
    metadata = json.loads(subprocess.check_output([str(candidate/'engines/ffmpeg/ffprobe.exe'),'-v','error',
        '-show_streams','-show_format','-of','json',str(movie)],text=True))
    assert abs(float(metadata['format']['duration'])-4)<.1
    assert {'audio','video'} <= {s['codec_type'] for s in metadata['streams']}
    for seconds, channel in [(0.5,0),(2.5,2)]:
        rgb = subprocess.check_output([str(candidate/'engines/ffmpeg/ffmpeg.exe'),'-v','error','-ss',str(seconds),
            '-i',str(movie),'-frames:v','1','-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
        assert len(rgb)==3 and rgb[channel]>200 and rgb[2-channel]<50, (label,seconds,list(rgb))
    for p in (png,webp):
        with Image.open(p) as image:
            image.load()
            assert image.size==(320,240) and image.mode=='RGBA'
            assert image.getpixel((0,0))[3]==0
    core = json.loads((ROOT / f'test-results/{label}-core-core.json').read_text())
    content = []
    for job in core['jobs']:
        for value in job['outputs']:
            p = Path(value)
            if p.suffix=='.jpg':
                with Image.open(p) as im, Image.open(job['sources'][0]) as source:
                    im.load()
                    assert im.size==source.size and im.mode=='RGB'
                    content.append({'kind':'image','size':im.size,'mode':im.mode})
            elif p.suffix=='.pdf':
                with pymupdf.open(p) as pdf:
                    text=''.join(page.get_text() for page in pdf)
                    assert len(pdf)>0
                    if job.get('operation')=='pdf.ocr':
                        assert '中文' in text and '轉檔測試' in text
                        kind='Chinese OCR'
                    else:
                        assert 'Matrix sentinel content 42' in text
                        kind='Office PDF'
                    content.append({'kind':kind,'pages':len(pdf),'text':text.strip()})
    checks.append({'package':label,'videoDuration':float(metadata['format']['duration']),'videoColorsVerified':True,
        'imagePNGWebPAlphaVerified':True,'core':content,'fixedWebView2':core['version']})
result={'passed':True,'checks':checks,'note':'OCR text is searchable and still requires proofreading.'}
(ROOT/'test-results/multimedia-packaged-content.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
