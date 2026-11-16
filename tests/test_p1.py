"""Focused P1 functional checks; generated content, no release packaging."""
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,image_plugins,command,hardware
from worker import convert
from detection import detect
from PIL import Image
import pymupdf

class P1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='p1-');cls.root=Path(cls.temp.name)
        cls.engines=locate(ROOT/'vendor');image_plugins();cls.verified=set()
        cls.image=cls.root/'中文 & image.png';Image.new('RGB',(80,40),'#4477aa').save(cls.image)
        cls.pdf=cls.root/'document.pdf'
        with pymupdf.open() as doc:
            page=doc.new_page();page.insert_text((72,72),'Alpha beta offline conversion',fontsize=14);doc.save(cls.pdf)
        cls.md=cls.root/'input.md';cls.md.write_text('# Heading\n\nAlpha **beta** offline conversion.',encoding='utf-8')
    @classmethod
    def tearDownClass(cls):
        if cls.verified:
            path=ROOT/'engine/verified-capabilities.json';old=set(json.loads(path.read_text())) if path.exists() else set()
            path.write_text(json.dumps(sorted(old|cls.verified),indent=2)+'\n')
        from fsutils import remove_tree
        remove_tree(cls.root,ROOT/'.tools');cls.temp.cleanup()
    def run_conversion(self,source,target,options=None):
        import uuid
        stage=self.root/uuid.uuid4().hex;stage.mkdir()
        src=detect(source,self.engines)['format']
        with contextlib.redirect_stdout(io.StringIO()):
            files=convert({'sources':[str(source)],'format':target,'options':options or {}},stage,self.engines)
        self.assertTrue(files);self.assertTrue(all(p.stat().st_size>0 for p in files))
        self.verified.add(src+':'+target)
        return files
    def test_images_heic_avif_gif(self):
        for fmt in ['heic','avif','gif']:
            path=self.run_conversion(self.image,fmt)[0]
            with Image.open(path) as img:self.assertEqual(img.size,(80,40));img.load()
            self.assertEqual(detect(path,self.engines)['format'],fmt)
            png=self.run_conversion(path,'png')[0]
            with Image.open(png) as img:self.assertEqual(img.size,(80,40))
        gif=self.root/'animated.gif'
        Image.new('RGB',(30,20),'red').save(gif,save_all=True,append_images=[Image.new('RGB',(30,20),'blue')],duration=[100,200],loop=0)
        for fmt in ['gif','webp']:
            path=self.run_conversion(gif,fmt)[0]
            with Image.open(path) as img:self.assertEqual(img.n_frames,2)
    def test_pdf_docx_and_text(self):
        result=self.run_conversion(self.pdf,'docx')[0]
        from docx import Document
        self.assertIn('Alpha beta', '\n'.join(p.text for p in Document(result).paragraphs))
        txt=self.run_conversion(self.pdf,'txt')[0];self.assertIn('offline',txt.read_text(encoding='utf-8'))
    def test_pandoc(self):
        html=self.run_conversion(self.md,'html')[0];self.assertIn('<h1',html.read_text(encoding='utf-8'))
        back=self.run_conversion(html,'md')[0];self.assertIn('Alpha',back.read_text(encoding='utf-8'))
        docx=self.run_conversion(self.md,'docx')[0]
        with zipfile.ZipFile(docx) as z:self.assertIn(b'Heading',z.read('word/document.xml'))
    def test_office_real_content(self):
        from docx import Document
        from openpyxl import Workbook,load_workbook
        from pptx import Presentation
        docx=self.root/'office.docx';d=Document();d.add_paragraph('Office content survives');d.save(docx)
        doc=self.run_conversion(docx,'doc')[0];back=self.run_conversion(doc,'docx')[0]
        self.assertIn('Office content', '\n'.join(p.text for p in Document(back).paragraphs))
        odt=self.run_conversion(docx,'odt')[0];self.run_conversion(odt,'docx')
        pdf=self.run_conversion(docx,'pdf')[0]
        with pymupdf.open(pdf) as d:self.assertIn('Office content',d[0].get_text())
        xlsx=self.root/'table.xlsx';w=Workbook();w.active.append(['Name','Value']);w.active.append(['Alpha',42]);w.save(xlsx)
        xls=self.run_conversion(xlsx,'xls')[0];back=self.run_conversion(xls,'xlsx')[0]
        self.assertEqual(load_workbook(back).active['B2'].value,42)
        ods=self.run_conversion(xlsx,'ods')[0];self.run_conversion(ods,'xlsx')
        csv=self.run_conversion(xlsx,'csv')[0];self.assertIn('Alpha',csv.read_text(encoding='utf-8-sig'))
        self.run_conversion(csv,'xlsx');self.run_conversion(xlsx,'pdf')
        pptx=self.root/'slides.pptx';r=Presentation();slide=r.slides.add_slide(r.slide_layouts[0]);slide.shapes.title.text='Presentation content';r.save(pptx)
        ppt=self.run_conversion(pptx,'ppt')[0];back=self.run_conversion(ppt,'pptx')[0]
        self.assertIn('Presentation content', '\n'.join(sh.text for sl in Presentation(back).slides for sh in sl.shapes if sh.has_text_frame))
        odp=self.run_conversion(pptx,'odp')[0];self.run_conversion(odp,'pptx');self.run_conversion(pptx,'pdf')
    def test_vectors(self):
        svg=self.root/'vector.svg';svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40"><rect width="80" height="40" fill="red"/></svg>')
        pdf=self.run_conversion(svg,'pdf')[0]
        with pymupdf.open(pdf) as d:self.assertEqual(len(d),1)
        eps=self.run_conversion(pdf,'eps')[0];png=self.run_conversion(eps,'png')[0]
        with Image.open(png) as img:img.load();self.assertGreater(img.width,10)
        self.run_conversion(pdf,'svg')
    def test_ebooks(self):
        import os
        html=self.root/'book.html';html.write_text('<html><head><title>Offline book</title></head><body><h1>Offline book</h1><p>Alpha content survives.</p></body></html>')
        epub=self.root/'book.epub'
        command([self.engines['calibre'],html,epub],env=dict(os.environ,CALIBRE_CONFIG_DIRECTORY=str(self.root/'calibre-config')))
        with zipfile.ZipFile(epub) as z:self.assertEqual(z.read('mimetype'),b'application/epub+zip')
        for fmt in ['mobi','azw3','fb2']:
            converted=self.run_conversion(epub,fmt)[0]
            back=self.run_conversion(converted,'epub')[0]
            with zipfile.ZipFile(back) as z:self.assertTrue(any('Alpha' in z.read(n).decode('utf-8','ignore') for n in z.namelist() if n.endswith(('.html','.xhtml'))))
    def test_media_hardware_fallback(self):
        video=self.root/'media.mp4'
        command([self.engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=s=160x120:r=10:d=1','-c:v','libx264',video])
        report=hardware(self.engines['ffmpeg']);self.assertTrue(next(d for d in report if d['id']=='cpu')['available'])
        out=self.run_conversion(video,'mp4',{'hardware':'auto','qualityPreset':'fast'})[0]
        from worker import probe
        self.assertEqual(probe(out,self.engines['ffprobe'])['streams'][0]['codec_type'],'video')
        out=self.run_conversion(video,'wmv',{'hardware':'cpu'})[0]
        self.assertEqual(probe(out,self.engines['ffprobe'])['streams'][0]['codec_name'],'wmv2')
    def test_async_hardware_does_not_block_inspection(self):
        import time
        from test_engine import Client
        client=Client(self.root/'async-service')
        try:
            start=time.monotonic();state=client.call('snapshot')
            self.assertLess(time.monotonic()-start,5)
            devices=client.call('hardware');self.assertEqual(len(devices),4)
            inspected=client.call('inspect',{'paths':[str(self.image)]})
            self.assertEqual(inspected[0]['extension'],'png');self.assertTrue(inspected[0]['available'])
        finally:client.close()

if __name__=='__main__':unittest.main(verbosity=2)
