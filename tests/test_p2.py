"""Focused toolbox tests validate actual decoded output and original preservation."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,command
from worker import convert,probe
from PIL import Image,ImageDraw,ImageFont
import pymupdf

class P2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='p2-');cls.root=Path(cls.temp.name)
        cls.engines=locate(ROOT/'vendor');cls.engines['hardwareCapabilities']=[{'id':'cpu','available':True,'codecs':{'h264':True,'h265':True}}]
        cls.image=cls.root/'原圖 & 空白.png';image=Image.new('RGB',(100,60),'red');ImageDraw.Draw(image).rectangle((40,20,55,35),fill='black');image.save(cls.image)
        cls.pdf=cls.root/'pages.pdf'
        with pymupdf.open() as doc:
            for text in ['Page one','Page two','Page three']:p=doc.new_page();p.insert_text((72,72),text)
            doc.save(cls.pdf)
        cls.video=cls.root/"影片 ' & 測試.mp4"
        command([cls.engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=s=160x128:r=12:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',cls.video])
        cls.originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [cls.image,cls.pdf,cls.video]}
    @classmethod
    def tearDownClass(cls):
        from fsutils import remove_tree
        remove_tree(cls.root,ROOT/'.tools');cls.temp.cleanup()
    def tearDown(self):
        for path,digest in self.originals.items():self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
    def execute(self,operation,sources,params=None):
        sources=sources if isinstance(sources,list) else [sources]
        stage=self.root/uuid.uuid4().hex;stage.mkdir();messages=io.StringIO()
        with contextlib.redirect_stdout(messages):files=convert({'operation':operation,'sources':list(map(str,sources)),'params':params or {},'options':{'hardware':'cpu'}},stage,self.engines)
        self.assertTrue(files);self.assertTrue(all(p.exists() for p in files))
        return files,messages.getvalue()
    def test_pdf_page_tools_and_watermark(self):
        files,_=self.execute('pdf.reorder',self.pdf,{'pages':'3,1,2'})
        with pymupdf.open(files[0]) as doc:self.assertIn('Page three',doc[0].get_text())
        files,_=self.execute('pdf.crop',self.pdf,{'region':[0,0,.5,.5]})
        with pymupdf.open(files[0]) as doc:self.assertAlmostEqual(doc[0].rect.width,297.5)
        files,_=self.execute('pdf.page-numbers',self.pdf,{'start':10})
        with pymupdf.open(files[0]) as doc:self.assertIn('10',doc[0].get_text())
        files,_=self.execute('pdf.compress',self.pdf,{'preset':'lossless'})
        with pymupdf.open(files[0]) as doc:self.assertEqual(len(doc),3);self.assertIn('Page two',doc[1].get_text())
        marked,_=self.execute('pdf.watermark',self.pdf,{'text':'Watermark','region':[.1,.3,.8,.3]})
        clean,_=self.execute('pdf.remove-watermark',marked[0])
        with pymupdf.open(clean[0]) as doc:
            self.assertIn('Page one',doc[0].get_text());self.assertNotIn('Watermark',doc[0].get_text())
        with self.assertRaisesRegex(ValueError,'找不到'):self.execute('pdf.remove-watermark',self.pdf)
    def test_pdf_password_and_secret_history(self):
        encrypted,_=self.execute('pdf.protect',self.pdf,{'password':'owned-p2-password'})
        with pymupdf.open(encrypted[0]) as doc:self.assertTrue(doc.needs_pass);self.assertTrue(doc.authenticate('owned-p2-password'))
        clear,_=self.execute('pdf.decrypt',encrypted[0],{'password':'owned-p2-password','authorized':True})
        with pymupdf.open(clear[0]) as doc:self.assertFalse(doc.needs_pass);self.assertIn('Page one',doc[0].get_text())
        from test_engine import Client
        client=Client(self.root/'secret-service')
        try:
            job=client.call('enqueue_tool',{'operation':'pdf.protect','sources':[str(self.pdf)],'params':{'password':'never-store-this-password'},'outputDir':str(self.root/'secret-output')})[0]
            done=client.wait([job['id']])[0];self.assertEqual(done['status'],'completed',done.get('error'))
            self.assertNotIn('password',done['params'])
            self.assertNotIn(b'never-store-this-password',(self.root/'secret-service/history.sqlite3').read_bytes())
        finally:client.close()
    def test_ocr_actual_text(self):
        image=Image.new('RGB',(1200,250),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',72);draw.text((50,70),'OFFLINE OCR TEST',fill='black',font=font)
        stream=io.BytesIO();image.save(stream,format='PNG');scanned=self.root/'scan.pdf'
        with pymupdf.open() as doc:p=doc.new_page(width=600,height=125);p.insert_image(p.rect,stream=stream.getvalue());doc.save(scanned)
        result,_=self.execute('pdf.ocr',scanned,{'language':'eng','onlyScans':True,'dpi':200})
        with pymupdf.open(result[0]) as doc:self.assertIn('OFFLINE OCR TEST',doc[0].get_text())
    def test_image_manipulation_and_metadata(self):
        result,_=self.execute('image.crop',self.image,{'region':[.1,.1,.5,.5]})
        with Image.open(result[0]) as image:self.assertEqual(image.size,(50,30))
        result,_=self.execute('image.resize',self.image,{'width':50,'height':0})
        with Image.open(result[0]) as image:self.assertEqual(image.size,(50,30))
        result,_=self.execute('image.rotate',self.image,{'angle':'90'})
        with Image.open(result[0]) as image:self.assertEqual(image.size,(60,100))
        repaired,_=self.execute('image.repair',self.image,{'region':[.39,.31,.2,.32]})
        with Image.open(repaired[0]) as image:self.assertGreater(image.convert('RGB').getpixel((47,27))[0],200)
        marked,_=self.execute('image.watermark',self.image,{'text':'TEST'})
        self.assertNotEqual(marked[0].read_bytes(),self.image.read_bytes())
        result,events=self.execute('image.compress',self.image,{'format':'jpg','targetMB':.000001,'minQuality':40})
        with Image.open(result[0]) as image:image.load()
        self.assertIn('"targetMet": false',events)
        exif=Image.Exif();exif[315]='unit-test';photo=self.root/'exif.jpg';Image.new('RGB',(40,30),'blue').save(photo,exif=exif)
        report,_=self.execute('image.metadata',photo);self.assertEqual(json.loads(report[0].read_text(encoding='utf-8'))[0]['exif']['Artist'],'unit-test')
        clean,_=self.execute('image.strip-metadata',photo)
        with Image.open(clean[0]) as image:self.assertFalse(image.getexif())
    def test_archive_formats_and_traversal(self):
        text=self.root/'中文 & text.txt';text.write_text('archive content',encoding='utf-8')
        for fmt in ['zip','7z','tar','gz']:
            packed,_=self.execute('archive.pack',text,{'format':fmt})
            listing,_=self.execute('archive.list',packed[0]);self.assertTrue(json.loads(listing[0].read_text(encoding='utf-8')))
            extracted,_=self.execute('archive.extract',packed[0])
            self.assertIn('archive content',''.join(p.read_text(encoding='utf-8') for p in extracted[0].rglob('*.txt')))
            if fmt!='zip':
                converted,_=self.execute('archive.convert',packed[0],{'format':'zip'})
                with zipfile.ZipFile(converted[0]) as z:self.assertIn(b'archive content',b''.join(z.read(n) for n in z.namelist() if not n.endswith('/')))
        for unsafe in ['../outside.txt','C:/outside.txt','safe.txt:payload','CON.txt']:
            bad=self.root/(uuid.uuid4().hex+'.zip')
            with zipfile.ZipFile(bad,'w') as z:z.writestr(unsafe,'malicious')
            with self.assertRaises(ValueError):self.execute('archive.extract',bad)
        link=self.root/'link.zip'
        with zipfile.ZipFile(link,'w') as z:
            entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=(0o120777<<16);z.writestr(entry,'../outside')
        with self.assertRaises(ValueError):self.execute('archive.extract',link)
    def test_file_hash_duplicates_and_copy_rename(self):
        other=self.root/'copy.png';other.write_bytes(self.image.read_bytes())
        report,_=self.execute('files.hash',self.image,{'expected':hashlib.sha256(self.image.read_bytes()).hexdigest()})
        self.assertTrue(json.loads(report[0].read_text(encoding='utf-8'))['files'][0]['matches'])
        report,_=self.execute('files.duplicates',[self.image,other]);self.assertEqual(len(json.loads(report[0].read_text(encoding='utf-8'))['groups']),1)
        result,_=self.execute('files.rename',[self.image,other],{'template':'new-{index}{ext}'})
        self.assertEqual([p.name for p in result],['new-1.png','new-2.png']);self.assertEqual(result[0].read_bytes(),self.image.read_bytes())
    def test_office_independent_watermarks(self):
        from docx import Document
        from docx.oxml import parse_xml
        doc=Document();doc.add_paragraph('Body content stays');doc.add_paragraph('Watermark')
        pict=parse_xml('<w:pict xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:v="urn:schemas-microsoft-com:vml"><v:shape id="PowerPlusWaterMarkObject1"><v:textpath string="Watermark"/></v:shape></w:pict>')
        doc.sections[0].header.paragraphs[0]._p.append(pict);source=self.root/'marked.docx';doc.save(source)
        result,_=self.execute('office.remove-watermark',source)
        text='\n'.join(p.text for p in Document(result[0]).paragraphs);self.assertIn('Body content stays',text);self.assertIn('Watermark',text)
        with zipfile.ZipFile(result[0]) as z:self.assertNotIn(b'PowerPlusWaterMarkObject',z.read('word/header1.xml'))
        from pptx import Presentation
        from pptx.util import Inches
        deck=Presentation();slide=deck.slides.add_slide(deck.slide_layouts[6]);shape=slide.shapes.add_textbox(Inches(1),Inches(1),Inches(4),Inches(1));shape.name='Watermark';shape.text='Watermark'
        body=slide.shapes.add_textbox(Inches(1),Inches(3),Inches(4),Inches(1));body.text='Presentation body stays';source=self.root/'marked.pptx';deck.save(source)
        result,_=self.execute('office.remove-watermark',source);text=' '.join(s.text for s in Presentation(result[0]).slides[0].shapes if s.has_text_frame)
        self.assertIn('Presentation body stays',text);self.assertNotIn('Watermark',text)
    def test_video_audio_tools(self):
        trimmed,_=self.execute('video.trim',self.video,{'start':.2,'end':1.2})
        self.assertAlmostEqual(float(probe(trimmed[0],self.engines['ffprobe'])['format']['duration']),1,delta=.2)
        merged,_=self.execute('video.merge',[self.video,self.video]);self.assertGreater(float(probe(merged[0],self.engines['ffprobe'])['format']['duration']),3.8)
        remuxed,events=self.execute('video.remux',self.video,{'format':'mkv'});self.assertIn('stream copy',events)
        self.assertEqual(probe(remuxed[0],self.engines['ffprobe'])['streams'][0]['codec_name'],'h264')
        animated,_=self.execute('video.gif',self.video,{'duration':1,'fps':5,'width':80})
        with Image.open(animated[0]) as image:self.assertGreater(image.n_frames,1)
        frame,_=self.execute('video.frame',self.video,{'time':.5})
        with Image.open(frame[0]) as image:self.assertEqual(image.size,(160,128))
        subtitle=self.root/'captions.srt';subtitle.write_text('1\n00:00:00,000 --> 00:00:01,500\nHello subtitle\n',encoding='utf-8')
        muxed,_=self.execute('video.mux-subtitles',[self.video,subtitle],{'format':'mkv'})
        extracted,_=self.execute('video.subtitles',muxed[0],{'stream':0,'format':'srt'});self.assertIn('Hello subtitle',extracted[0].read_text(encoding='utf-8'))
        repaired,_=self.execute('video.delogo',self.video,{'region':[.2,.2,.25,.25]});self.assertTrue(probe(repaired[0],self.engines['ffprobe'])['streams'])
        normalized,_=self.execute('audio.normalize',self.video,{'format':'wav','lufs':-16,'peak':-1.5})
        info=probe(normalized[0],self.engines['ffprobe']);self.assertEqual(info['streams'][0]['codec_type'],'audio')
        audio,_=self.execute('audio.trim',normalized[0],{'start':.2,'end':1.2,'format':'flac'})
        self.assertAlmostEqual(float(probe(audio[0],self.engines['ffprobe'])['format']['duration']),1,delta=.15)
    def test_chinese_ocr_and_verbatim_runtime(self):
        from PIL import ImageDraw,ImageFont
        from test_engine import Client
        from unittest.mock import patch
        import os,io,time
        image=Image.new('RGB',(1500,260),'white');ImageDraw.Draw(image).text((60,60),'繁體中文轉檔測試',fill='black',font=ImageFont.truetype(self.engines['font'],100))
        data=io.BytesIO();image.save(data,format='PNG');source=self.root/'繁中 scan.pdf'
        with pymupdf.open() as doc:
            doc.new_page(width=750,height=130).insert_image(pymupdf.Rect(0,0,750,130),stream=data.getvalue());doc.save(source)
        engine_path=self.root/'中文引擎 & runtime';(engine_path/'tessdata').mkdir(parents=True)
        import shutil
        for file in Path(self.engines['tessdata']).glob('*.traineddata'):shutil.copy2(file,engine_path/'tessdata'/file.name)
        engine_root=str(engine_path)
        if os.name=='nt' and not engine_root.startswith('\\\\?\\'):engine_root='\\\\?\\'+engine_root
        with patch.dict(os.environ,{'FILE_CONVERTER_TEST_ENGINES':engine_root}):client=Client(self.root/'cjk-verbatim-data')
        try:
            self.assertFalse(client.call('engines')['tessdata'].startswith('\\\\?\\'))
            job=client.call('enqueue_tool',{'operation':'pdf.ocr','sources':[str(source)],'params':{'language':'eng+chi_tra','dpi':200},'outputDir':str(self.root/'cjk-output')})[0]
            result=client.wait([job['id']])[0];self.assertEqual(result['status'],'completed',result.get('error'))
            with pymupdf.open(result['outputs'][0]) as document:text=''.join(''.join(page.get_text().split()) for page in document)
            self.assertIn('中文轉檔測試',text);self.assertEqual(job['params']['language'],'chi_tra+eng')
        finally:client.close()

    def test_delogo_preview_clip(self):
        from test_engine import Client
        from worker import probe
        source=self.root/'preview-12s.mp4'
        command([self.engines['ffmpeg'],'-v','error','-f','lavfi','-i','color=c=gray:s=160x120:r=12:d=12','-vf','drawbox=x=30:y=30:w=35:h=25:color=red:t=fill','-c:v','libx264','-preset','ultrafast',source])
        client=Client(self.root/'delogo-preview-service')
        try:
            job=client.call('enqueue_tool',{'operation':'video.delogo','sources':[str(source)],'params':{'region':[.18,.24,.25,.24]},'options':{'hardware':'cpu'},'preview':True})[0]
            import time
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                task=client.call('preview_status',{'id':job['id']})
                if task['status'] in {'failed','completed','cancelled'}:break
                time.sleep(.1)
            self.assertEqual(task['status'],'completed',task.get('error'))
            duration=float(probe(task['outputs'][0],self.engines['ffprobe'])['format']['duration']);self.assertAlmostEqual(duration,10,places=1)
            self.assertFalse(client.call('snapshot')['jobs']);client.call('clear_preview',{'id':job['id']})
        finally:client.close()

    def test_preview_queue_and_folder_publication(self):
        from test_engine import Client
        import time
        client=Client(self.root/'preview-service')
        try:
            job=client.call('enqueue_tool',{'operation':'image.crop','sources':[str(self.image)],'params':{'region':[0,0,.5,.5]},'preview':True})[0]
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                task=client.call('preview_status',{'id':job['id']})
                if task['status'] in {'completed','failed','cancelled'}:break
                time.sleep(.1)
            self.assertEqual(task['status'],'completed',task.get('error'))
            rendered=client.call('preview',{'path':task['outputs'][0]});self.assertTrue(rendered['image'].startswith('data:image/png'))
            self.assertFalse(client.call('snapshot')['jobs']);client.call('clear_preview',{'id':job['id']})
            self.assertFalse(Path(job['outputDir']).exists())
            packed,_=self.execute('archive.pack',self.image,{'format':'zip'})
            job=client.call('enqueue_tool',{'operation':'archive.extract','sources':[str(packed[0])],'outputDir':str(self.root/'published')})[0]
            completed=client.wait([job['id']])[0];self.assertEqual(completed['status'],'completed',completed.get('error'));self.assertTrue(Path(completed['outputs'][0]).is_dir())
        finally:client.close()

if __name__=='__main__':unittest.main(verbosity=2)
