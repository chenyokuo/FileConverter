"""End-to-end subprocess tests with generated fixtures; no user files or network."""
import base64
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine'))
from formats import outputs
from PIL import Image
import pymupdf
import psutil

class Client:
    def __init__(self,root):
        command=[sys.executable,str(ROOT/'engine/service.py')]
        if os.environ.get('RAI_TEST_FROZEN'):command=[os.environ['RAI_TEST_FROZEN']]
        self.proc=subprocess.Popen(command+['--data',str(root),'--engines',str(ROOT/'vendor')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.messages=queue.Queue();self.events=[];self.serial=0
        def read():
            for line in self.proc.stdout:
                try:self.messages.put(json.loads(line))
                except ValueError:pass
        threading.Thread(target=read,daemon=True).start()
    def call(self,method,args=None):
        self.serial+=1
        self.proc.stdin.write((json.dumps({'id':self.serial,'method':method,'args':args or {}},ensure_ascii=False)+'\n').encode('utf-8'));self.proc.stdin.flush()
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            try:message=self.messages.get(timeout=1)
            except queue.Empty:
                if self.proc.poll() is not None:raise AssertionError(self.proc.stderr.read().decode(errors='replace'))
                continue
            if message.get('event'):self.events.append(message['data']);continue
            if message.get('id')==self.serial:
                if 'error' in message:raise ValueError(message['error'])
                return message['result']
        raise AssertionError('Service request timed out')
    def wait(self,ids,timeout=40):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            jobs={j['id']:j for j in self.call('snapshot')['jobs']}
            if all(jobs[i]['status'] in {'completed','cancelled','failed'} for i in ids):return [jobs[i] for i in ids]
            time.sleep(.08)
        raise AssertionError('Job timeout')
    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:self.proc.kill();raise
        if not self.proc.stdin.closed:self.proc.stdin.close()
        self.proc.stdout.close();self.proc.stderr.close()

class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='rai-tests-',dir=ROOT/'.tools')
        cls.root=Path(cls.temp.name);cls.inputs=cls.root/'中文 路徑 [input] & 特殊';cls.inputs.mkdir()
        cls.image=cls.inputs/'照片 alpha & 空白.png';Image.new('RGBA',(80,40),(255,0,0,128)).save(cls.image)
        cls.image2=cls.inputs/'第二張.webp';Image.new('RGB',(50,70),'blue').save(cls.image2)
        cls.pdf=cls.inputs/'文件 中文.pdf'
        with pymupdf.open() as d:
            for text in ['Page one','Page two','Page three']:p=d.new_page();p.insert_text((72,72),text)
            d.save(cls.pdf)
        cls.video=cls.inputs/'影片 & 聲音.mp4';cls.ffmpeg=ROOT/'vendor/ffmpeg/ffmpeg.exe'
        if cls.ffmpeg.is_file():
            subprocess.run([str(cls.ffmpeg),'-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:v','libx264','-preset','ultrafast','-c:a','aac',str(cls.video)],check=True)
            cls.long=cls.inputs/'長影片.mp4'
            subprocess.run([str(cls.ffmpeg),'-v','error','-f','lavfi','-i','testsrc2=size=1280x720:rate=30','-t','25','-c:v','libx264','-preset','ultrafast',str(cls.long)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.dir=self.root/uuid_name();self.client=Client(self.dir/'data');self.out=self.dir/'輸出 & output'
    def tearDown(self):self.client.close()
    def enqueue(self,source,fmt,opt=None):
        sources=[str(p) for p in source] if isinstance(source,list) else [str(source)]
        return self.client.call('enqueue',{'jobs':[{'sources':sources,'format':fmt,'outputDir':str(self.out),'options':opt or {}}]})[0]
    def finish(self,job):
        result=self.client.wait([job['id']])[0];self.assertEqual(result['status'],'completed',result.get('error'));return result
    def test_01_matrix(self):
        self.assertNotIn('xlsx',outputs('docx'));self.assertNotIn('mp4',outputs('pdf'));self.assertIn('pdf',outputs('xlsx'));self.assertIn('mp3',outputs('mov'));self.assertEqual(outputs('exe'),[])
    def test_02_image_resize_alpha_collision_original(self):
        digest=hashlib.sha256(self.image.read_bytes()).hexdigest()
        job=self.finish(self.enqueue(self.image,'jpg',{'width':40,'matte':'#ffffff'}))
        with Image.open(job['outputs'][0]) as image:
            self.assertEqual(image.size,(40,20));self.assertEqual(image.mode,'RGB');self.assertGreater(image.getpixel((0,0))[1],100)
        again=self.finish(self.enqueue(self.image,'jpg'))
        self.assertNotEqual(job['outputs'],again['outputs']);self.assertEqual(hashlib.sha256(self.image.read_bytes()).hexdigest(),digest)
    def test_03_image_all_formats(self):
        for fmt in ['png','webp','bmp','tiff']:
            job=self.finish(self.enqueue(self.image,fmt));self.assertTrue(Path(job['outputs'][0]).is_file())
    def test_04_pdf_merge_split_rotate_extract(self):
        merged=self.finish(self.enqueue([self.image,self.pdf,self.image2],'pdf'))
        with pymupdf.open(merged['outputs'][0]) as d:self.assertEqual(len(d),5)
        extracted=self.finish(self.enqueue(self.pdf,'pdf',{'pages':'1,3','rotation':90,'split':True}))
        self.assertEqual(len(extracted['outputs']),2)
        for p in extracted['outputs']:
            with pymupdf.open(p) as d:self.assertEqual(len(d),1);self.assertEqual(d[0].rotation,90)
        with pymupdf.open(extracted['outputs'][1]) as d:self.assertIn('Page three',d[0].get_text())
    def test_05_pdf_raster(self):
        for fmt in ['png','jpg']:
            job=self.finish(self.enqueue(self.pdf,fmt,{'pdfDpi':72}));self.assertEqual(len(job['outputs']),3)
            with Image.open(job['outputs'][0]) as image:self.assertEqual(image.size,(595,842))
    def test_06_failure_does_not_abort_batch(self):
        bad=self.inputs/'破損.png';bad.write_bytes(b'not an image')
        jobs=[self.enqueue(bad,'webp'),self.enqueue(self.image2,'png')]
        result=self.client.wait([j['id'] for j in jobs]);self.assertEqual([j['status'] for j in result],['failed','completed']);self.assertTrue(result[0]['error'])
    def test_07_background_and_settings_persist(self):
        image=self.client.call('background',{'path':str(self.image)})
        self.assertTrue(image.startswith('data:image/webp;base64,'));self.assertEqual(base64.b64decode(image.split(',')[1]),(self.dir/'data/background.webp').read_bytes())
        import io
        with Image.open(io.BytesIO(base64.b64decode(image.split(',')[1]))) as saved:
            self.assertEqual(saved.size,(80,40))
            self.assertEqual(saved.convert('RGBA').getpixel((0,0)),(255,0,0,128))
        settings={'concurrency':3,'appearance':{'image':image,'imageOpacity':37,'materials':{'card':{'opacity':22,'blur':31}}}}
        self.client.call('settings',{'settings':settings});self.client.close();self.client=Client(self.dir/'data')
        self.assertEqual(self.client.call('snapshot')['settings'],settings)
    def test_08_history_retry_clear(self):
        job=self.finish(self.enqueue(self.image,'png'));self.client.close();self.client=Client(self.dir/'data')
        self.assertEqual(self.client.call('snapshot')['jobs'][0]['status'],'completed')
        retry=self.client.call('retry',{'id':job['id']})[0];self.finish(retry);self.client.call('clear')
        self.assertEqual(self.client.call('snapshot')['jobs'],[]);self.assertTrue(Path(job['outputs'][0]).exists())
    def test_09_media_audio_and_real_progress(self):
        if not self.ffmpeg.is_file():self.skipTest('FFmpeg absent')
        converted=self.finish(self.enqueue(self.video,'webm',{'videoHeight':144,'crf':32}))
        audio=self.finish(self.enqueue(self.video,'mp3',{'audioBitrate':128,'sampleRate':44100,'channels':1}))
        from worker import probe
        fp=str(ROOT/'vendor/ffmpeg/ffprobe.exe')
        info=probe(converted['outputs'][0],fp);self.assertEqual(info['streams'][0]['height'],144)
        sound=probe(audio['outputs'][0],fp);self.assertEqual(sound['streams'][0]['channels'],1);self.assertEqual(sound['streams'][0]['sample_rate'],'44100')
        progress=[e['progress'] for e in self.client.events if e['id']==converted['id'] and e['status']=='running'];self.assertTrue(any(p>0 for p in progress),progress)
    def test_10_cancel_process_tree(self):
        if not self.ffmpeg.is_file():self.skipTest('FFmpeg absent')
        job=self.enqueue(self.long,'mp4',{'videoCodec':'h265','crf':18,'videoHeight':1080})
        deadline=time.monotonic()+15;children=[]
        while time.monotonic()<deadline:
            children=psutil.Process(self.client.proc.pid).children(recursive=True)
            if any('ffmpeg' in c.name().lower() for c in children):break
            time.sleep(.1)
        self.assertTrue(any('ffmpeg' in c.name().lower() for c in children))
        # A venv's python.exe redirector may have the service interpreter as a child.
        # Only task workers / encoders should stop on cancellation, not the service.
        task_children=[c for c in children if '--worker' in c.cmdline() or 'ffmpeg' in c.name().lower()]
        self.client.call('cancel',{'id':job['id']});result=self.client.wait([job['id']])[0];self.assertEqual(result['status'],'cancelled')
        gone,alive=psutil.wait_procs(task_children,timeout=5)
        self.assertFalse(alive,[(c.pid,c.name(),c.status()) for c in alive]);self.assertFalse(list(self.out.glob('.rai-*')));self.assertFalse(list(self.out.glob('*.mp4')))
    def test_11_queued_cancel_and_parallel_limit(self):
        self.client.call('settings',{'settings':{'concurrency':1}})
        jobs=[self.enqueue(self.image,'webp') for _ in range(15)]
        self.client.call('cancel',{'id':jobs[-1]['id']});result=self.client.wait([j['id'] for j in jobs]);self.assertEqual(result[-1]['status'],'cancelled')
        self.assertEqual(sum(j['status']=='completed' for j in result),14,[(j['status'],j.get('error')) for j in result])
    def test_12_missing_office_and_invalid_request(self):
        with self.assertRaises(ValueError):self.enqueue(self.pdf,'docx')
        with self.assertRaises(ValueError):self.client.call('shell',{'command':'whoami'})
        with self.assertRaises(ValueError):self.client.call('settings',{'settings':{'concurrency':10}})
    def test_13_bulk_inspect(self):
        result=self.client.call('inspect',{'paths':[str(self.image)]*250});self.assertEqual(len(result),250);self.assertTrue(result[0]['preview']);self.assertEqual(result[0]['dimensions'],[80,40])
    def test_14_offline_engines_discovered(self):
        engines=self.client.call('engines');self.assertTrue(engines['ffmpeg']);self.assertTrue(engines['ffprobe'])
    def test_15_abrupt_shutdown_kills_children(self):
        if not self.ffmpeg.is_file() or os.name!='nt':self.skipTest('Windows FFmpeg test')
        job=self.enqueue(self.long,'mp4',{'videoCodec':'h265','videoHeight':1080})
        deadline=time.monotonic()+15;children=[]
        while time.monotonic()<deadline:
            children=psutil.Process(self.client.proc.pid).children(recursive=True)
            if any('ffmpeg' in c.name().lower() for c in children):break
            time.sleep(.1)
        self.assertTrue(children);self.client.proc.kill();self.client.proc.wait();time.sleep(.5)
        self.assertFalse(any(c.is_running() for c in children))
        self.client.close();self.client=Client(self.dir/'data')
        snapshot=self.client.call('snapshot');self.assertEqual(snapshot['jobs'][0]['status'],'cancelled')
    def test_16_all_media_output_containers(self):
        if not self.ffmpeg.is_file():self.skipTest('FFmpeg absent')
        from worker import probe
        fp=str(ROOT/'vendor/ffmpeg/ffprobe.exe')
        for fmt in outputs('mp4'):
            with self.subTest(format=fmt):
                job=self.finish(self.enqueue(self.video,fmt))
                info=probe(job['outputs'][0],fp)
                self.assertGreater(float(info['format']['duration']),2)
                self.assertTrue(info['streams'])
    def test_17_missing_office_dependency_error(self):
        if self.client.call('engines')['soffice']:self.skipTest('LibreOffice is present')
        source=self.inputs/'test.docx';source.write_bytes(b'placeholder; adapter must fail explicitly before invoking a missing engine')
        job=self.enqueue(source,'pdf');result=self.client.wait([job['id']])[0]
        self.assertEqual(result['status'],'failed');self.assertIn('LibreOffice',result['error'])

def uuid_name():
    import uuid
    return uuid.uuid4().hex

if __name__=='__main__':unittest.main(verbosity=2)
