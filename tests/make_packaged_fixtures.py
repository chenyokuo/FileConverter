"""Prepare small original QA inputs from source, without ignored runtime/test-file copies."""
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
from docx import Document
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,command
base=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'.tools'
assert base.is_relative_to(ROOT/'.tools')
base.mkdir(parents=True,exist_ok=True)
engines=locate(ROOT/'vendor')
subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tests/make_ui_fixtures.py'),'--directory',str(base/'ui-fixtures')],check=True)
media=base/'editor-ui';media.mkdir(exist_ok=True)
for name,color in [('red','red'),('blue','blue')]:
    target=media/(name+'.mp4')
    if not target.exists():
        command([engines['ffmpeg'],'-v','error','-f','lavfi','-i',f'color=c={color}:s=320x180:r=20:d=2',
            '-f','lavfi','-i','sine=f=440:d=2','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',target])
alpha=media/'alpha.png'
if not alpha.exists():
    image=Image.new('RGBA',(320,240));ImageDraw.Draw(image).rectangle((20,20,299,219),fill='red');image.save(alpha)
matrix=base/'p5-matrix';matrix.mkdir(exist_ok=True)
office=matrix/'來源 中文 & docx.docx'
if not office.exists():
    doc=Document();doc.add_paragraph('Matrix sentinel content 42');doc.save(office)
ocr=base/'p5-installed-fixtures';ocr.mkdir(exist_ok=True)
scan=ocr/'繁中掃描.pdf'
if not scan.exists():
    image=Image.new('RGB',(1600,280),'white');ImageDraw.Draw(image).text((40,40),'繁體中文轉檔測試',
        font=ImageFont.truetype(engines['font'],100),fill='black')
    import io
    buffer=io.BytesIO();image.save(buffer,format='PNG')
    with pymupdf.open() as doc:
        page=doc.new_page(width=800,height=140);page.insert_image(page.rect,stream=buffer.getvalue());doc.save(scan)
print('Prepared small original native/editor/Office/OCR fixtures:',base)
