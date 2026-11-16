"""Exercise every advertised directed edge using generated content, resumable evidence.
Not a package-import test: decode images/frames/pages/audio and inspect document bodies.
Run once at P5; --failed retries only failed/unrun pairs after a relevant repair.
"""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import os
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,command,image_plugins
from registry import capabilities,category
from detection import detect
from worker import convert,probe
from PIL import Image,ImageStat
import pymupdf
STAGE=ROOT/'.tools/p5-matrix';STAGE.mkdir(exist_ok=True)
RESULTS=ROOT/'test-results/matrix.json';RESULTS.parent.mkdir(exist_ok=True)
engines=locate(ROOT/'vendor');image_plugins();sources={};counter=0
def convert_one(source,target,options=None,label='fixture'):
    global counter
    counter+=1;stage=STAGE/f'{label}-{counter}';stage.mkdir(exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):files=convert({'sources':[str(source)],'format':target,'options':{'hardware':'cpu','qualityPreset':'fast','pdfDpi':72,**(options or {})}},stage,engines)
    if not files or not all(p.is_file() and p.stat().st_size for p in files):raise AssertionError('No readable outputs')
    return files
def fixture(fmt,source=None):
    dest=STAGE/('來源 中文 & '+fmt+'.'+fmt)
    if source and not dest.exists():dest.write_bytes(convert_one(source,fmt)[0].read_bytes())
    sources[fmt]=dest;return dest
image=fixture('png')
if not image.exists():Image.new('RGB',(120,80),'#bc5423').save(image)
for fmt in ['jpg','webp','bmp','tiff','gif','heic','avif']:fixture(fmt,image)
pdf=fixture('pdf')
if not pdf.exists():
    with pymupdf.open() as doc:p=doc.new_page();p.insert_text((72,72),'Matrix sentinel content 42');doc.save(pdf)
video=fixture('mp4')
if not video.exists():command([engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=s=320x240:r=12:d=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',video])
for fmt in ['mov','mkv','avi','webm','wmv','mp3','wav','flac','aac','m4a','ogg','opus']:fixture(fmt,video)
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
docx=fixture('docx');xlsx=fixture('xlsx');pptx=fixture('pptx')
if not docx.exists():d=Document();d.add_paragraph('Matrix sentinel content 42');d.save(docx)
if not xlsx.exists():d=Workbook();d.active.append(['Matrix sentinel content',42]);d.save(xlsx)
if not pptx.exists():d=Presentation();d.slides.add_slide(d.slide_layouts[0]).shapes.title.text='Matrix sentinel content 42';d.save(pptx)
for fmt in ['doc','odt','rtf']:fixture(fmt,docx)
for fmt in ['xls','ods']:fixture(fmt,xlsx)
for fmt in ['ppt','odp']:fixture(fmt,pptx)
for fmt,text in [('txt','Matrix sentinel content 42'),('md','# Matrix sentinel content 42\n\nBody paragraph.'),('html','<html><head><title>Matrix</title></head><body><p>Matrix sentinel content 42</p></body></html>'),('csv','Name,Value\nMatrix sentinel content,42\n'),('tsv','Name\tValue\nMatrix sentinel content\t42\n')]:
    path=fixture(fmt)
    if not path.exists():path.write_text(text,encoding='utf-8')
svg=fixture('svg')
if not svg.exists():svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="red"/></svg>',encoding='utf-8')
fixture('eps',pdf)
epub=fixture('epub')
if not epub.exists():command([engines['calibre'],sources['html'],epub],env=dict(os.environ,CALIBRE_CONFIG_DIRECTORY=str(STAGE/'calibre-config')))
for fmt in ['mobi','azw3','fb2']:fixture(fmt,epub)
from archives import pack,extract
for fmt in ['zip','7z','tar','gz']:
    path=fixture(fmt)
    if not path.exists():pack([sources['txt']],path,fmt,engines)
rar=ROOT/'.tools/test-fixtures/rar5-stored.rar'
if rar.is_file():sources['rar']=rar
results=json.loads(RESULTS.read_text(encoding='utf-8')) if '--failed' in sys.argv and RESULTS.exists() else {}
for edge in capabilities(engines):
    key=edge['id']
    if '--failed' in sys.argv and results.get(key,{}).get('status')=='passed':continue
    start=time.monotonic()
    try:
        source=sources[edge['source']]
        assert detect(source,engines)['format']==edge['source'],f'Source content detection differs: {detect(source,engines)}'
        files=convert_one(source,edge['target'],{'rotation':90} if edge['operationRequired'] else {},key.replace(':','-'))
        for file in files:
            target=edge['target'];actual=detect(file,engines)['format']
            assert actual==target,f'Output content {actual}, expected {target}: {detect(file,engines)}'
            kind=category(target)
            if kind=='image':
                with Image.open(file) as img:img.load();assert img.width>0 and img.height>0;assert max(ImageStat.Stat(img.convert('RGB')).mean)>0
            elif kind=='pdf':
                with pymupdf.open(file) as doc:
                    assert len(doc)>0;pix=doc[0].get_pixmap();assert len(pix.samples)>0
                    if category(edge['source']) in {'office','pdf'}:assert 'Matrix' in ''.join(p.get_text() for p in doc),'Document text lost'
            elif kind in {'video','audio'}:
                info=probe(file,engines['ffprobe']);assert float(info['format']['duration'])>.5
                command([engines['ffmpeg'],'-v','error','-i',file,'-t','0.25','-f','null','-'],timeout=30)
            elif target in {'docx','xlsx','pptx','odt','ods','odp'}:
                with zipfile.ZipFile(file) as archive:
                    assert archive.testzip() is None
                    body=''.join(archive.read(n).decode('utf-8','ignore') for n in archive.namelist() if n.endswith('.xml'))
                    assert 'Matrix' in body,'Document body lost'
            elif target in {'doc','xls','ppt','rtf'}:
                rendered=convert_one(file,'pdf')[0]
                with pymupdf.open(rendered) as doc:assert 'Matrix' in ''.join(p.get_text() for p in doc),'Legacy content lost'
            elif kind=='office':assert 'Matrix' in file.read_text(encoding='utf-8-sig'),'Text content lost'
            elif kind=='ebook':
                check=file if target=='epub' else convert_one(file,'epub')[0]
                with zipfile.ZipFile(check) as archive:assert any('Matrix' in archive.read(n).decode('utf-8','ignore') for n in archive.namelist() if n.endswith(('.html','.xhtml')))
            elif kind=='vector':
                rendered=convert_one(file,'png')[0]
                with Image.open(rendered) as image:image.load();assert image.width>0
            elif kind=='archive':
                folder=STAGE/f'check-{counter}';extract(file,folder,engines)
                assert any(p.is_file() and p.stat().st_size for p in folder.rglob('*'))
        results[key]={'status':'passed','seconds':round(time.monotonic()-start,2),'outputs':len(files)};print('PASS',key,flush=True)
    except Exception as error:results[key]={'status':'failed','error':str(error),'seconds':round(time.monotonic()-start,2)};print('FAIL',key,str(error),flush=True)
    RESULTS.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
verified=sorted(key for key,result in results.items() if result['status']=='passed')
(ROOT/'engine/verified-capabilities.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8')
print('Matrix:',len(verified),'passed;',len(results)-len(verified),'failed',flush=True)
sys.exit(any(result['status']!='passed' for result in results.values()))
