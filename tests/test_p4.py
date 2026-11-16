"""Focused P4 checks: real pipelines, watch lifecycle, previews and shell key boundaries."""
from pathlib import Path
import hashlib
import os
import sys
import tempfile
import time
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from test_engine import Client
from PIL import Image
import pymupdf
from runtime import command,locate
from worker import probe

class P4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='p4-');cls.root=Path(cls.temp.name);cls.engines=locate(ROOT/'vendor')
        cls.image=cls.root/'原圖 & source.png';Image.new('RGB',(200,100),'#359bd2').save(cls.image)
        cls.pdf=cls.root/'document.pdf'
        with pymupdf.open() as d:
            for text in ['Workflow original text','Second page']:p=d.new_page();p.insert_text((72,72),text)
            d.save(cls.pdf)
        cls.video=cls.root/'owned.mov';command([cls.engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=12:duration=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',cls.video])
    @classmethod
    def tearDownClass(cls):
        from fsutils import remove_tree
        remove_tree(cls.root,ROOT/'.tools');cls.temp.cleanup()
    def setUp(self):
        self.dir=self.root/uuid.uuid4().hex;self.client=Client(self.dir/'data');self.out=self.dir/'outputs'
    def tearDown(self):self.client.close()
    def config(self,source,steps,onError='abort'):return {'name':'驗證流程','source':source,'steps':steps,'onError':onError}
    def enqueue(self,config,paths):return self.client.call('enqueue_workflow',{'config':config,'paths':[str(p) for p in paths],'outputDir':str(self.out)})
    def complete(self,jobs):
        result=self.client.wait([j['id'] for j in jobs],timeout=90)
        self.assertTrue(all(j['status']=='completed' for j in result),result);return result
    def test_image_pipeline_batch_and_presets_persist(self):
        config=self.config('png',[{'type':'tool','operation':'image.resize','params':{'width':80,'format':'webp'}},{'type':'tool','operation':'image.strip-metadata','params':{'format':'webp'}},{'type':'tool','operation':'files.rename','params':{'template':'done-{stem}{ext}'}}])
        planned=self.client.call('plan_workflow',{'config':config});self.assertEqual(planned['target'],'webp')
        jobs=self.complete(self.enqueue(config,[self.image,self.image]));self.assertNotEqual(jobs[0]['outputs'],jobs[1]['outputs'])
        for job in jobs:
            with Image.open(job['outputs'][0]) as image:self.assertEqual(image.size,(80,40));self.assertFalse(image.getexif())
            self.assertTrue(Path(job['outputs'][0]).name.startswith('done-'));self.assertEqual(len(job['stats']['workflowLog']),3)
        preset=self.config('png',[{'type':'convert','target':'jpg','options':{'quality':75}}]);item=self.client.call('save_automation',{'kind':'preset','config':preset})
        item=self.client.call('save_automation',{'id':item['id'],'kind':'preset','config':dict(preset,name='Edited preset')})
        self.client.close();self.client=Client(self.dir/'data');state=self.client.call('automation');self.assertEqual(state['items'][0]['name'],'Edited preset')
        self.client.call('delete_automation',{'id':item['id']});self.assertEqual(self.client.call('automation')['items'],[])
    def test_pdf_ocr_docx_rename_and_h265(self):
        config=self.config('pdf',[{'type':'tool','operation':'pdf.ocr','params':{'language':'eng','onlyScans':True}},{'type':'convert','target':'docx'},{'type':'tool','operation':'files.rename','params':{'template':'final{ext}'}}])
        job=self.complete(self.enqueue(config,[self.pdf]))[0]
        from docx import Document
        self.assertIn('Workflow original text','\n'.join(p.text for p in Document(job['outputs'][0]).paragraphs))
        config=self.config('mov',[{'type':'convert','target':'mp4','options':{'videoCodec':'h265','hardware':'cpu','qualityPreset':'fast','crf':30}}])
        job=self.complete(self.enqueue(config,[self.video]))[0];streams=probe(job['outputs'][0],self.engines['ffprobe'])['streams'];self.assertTrue(any(s['codec_name']=='hevc' for s in streams))
    def test_abort_skip_and_reject_invalid_paths(self):
        steps=[{'type':'tool','operation':'pdf.remove-watermark'},{'type':'convert','target':'txt'}]
        failed=self.client.wait([j['id'] for j in self.enqueue(self.config('pdf',steps),[self.pdf])])[0];self.assertEqual(failed['status'],'failed');self.assertEqual(failed['outputs'],[])
        job=self.complete(self.enqueue(self.config('pdf',steps,'skip'),[self.pdf]))[0];self.assertIn('Workflow original text',Path(job['outputs'][0]).read_text(encoding='utf-8'));self.assertEqual(job['stats']['workflowLog'][0]['status'],'failed')
        with self.assertRaisesRegex(ValueError,'不支援'):self.client.call('plan_workflow',{'config':self.config('pdf',[{'type':'convert','target':'mp4'}])})
        with self.assertRaises(ValueError):self.client.call('plan_workflow',{'config':self.config('pdf',[{'type':'tool','operation':'pdf.protect','params':{'password':'secret'}}])})
        with self.assertRaises(ValueError):self.enqueue(self.config('pdf',[{'type':'convert','target':'txt'}]),[self.image])
    def test_watches_wait_dedupe_pause_stop_restart(self):
        source=self.dir/'watch';source.mkdir(parents=True);existing=source/'existing.png';existing.write_bytes(self.image.read_bytes())
        config=self.config('png',[{'type':'convert','target':'webp','options':{'width':64}}])
        with self.assertRaisesRegex(ValueError,'重疊'):self.client.call('save_automation',{'kind':'watch','config':config,'sourceDir':str(source),'outputDir':str(source/'out')})
        item=self.client.call('save_automation',{'kind':'watch','config':config,'sourceDir':str(source),'outputDir':str(self.out)})
        self.client.call('watch_action',{'id':item['id'],'action':'start'})
        new=source/'new 中文.png';data=self.image.read_bytes()
        with new.open('wb') as stream:
            stream.write(data[:20]);stream.flush();time.sleep(.7);stream.write(data[20:]);stream.flush();time.sleep(2.1)
            self.assertFalse(self.client.call('snapshot')['jobs'],'Must not read a still-open writer')
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            jobs=self.client.call('snapshot')['jobs']
            if jobs:break
            time.sleep(.2)
        self.assertEqual(len(jobs),1);self.complete(jobs)
        os.utime(new,None);time.sleep(2.5);self.assertEqual(len(self.client.call('snapshot')['jobs']),1,'Same content must not enqueue again')
        self.client.call('watch_action',{'id':item['id'],'action':'pause'});(source/'paused.png').write_bytes(data);time.sleep(2);self.assertEqual(len(self.client.call('snapshot')['jobs']),1)
        self.client.call('watch_action',{'id':item['id'],'action':'start'});deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if len(self.client.call('snapshot')['jobs'])==2:break
            time.sleep(.2)
        self.assertEqual(len(self.client.call('snapshot')['jobs']),2)
        self.client.call('watch_action',{'id':item['id'],'action':'stop'});(source/'stopped.png').write_bytes(data);time.sleep(2);self.assertEqual(len(self.client.call('snapshot')['jobs']),2)
        self.client.close();self.client=Client(self.dir/'data');state=self.client.call('automation');self.assertEqual(state['states'],{});self.assertEqual(len(state['items']),1)
        self.client.call('delete_automation',{'id':item['id']})
    def test_real_pdf_document_audio_video_previews(self):
        pdf=self.client.call('preview',{'path':str(self.pdf),'page':1});self.assertEqual(pdf['metadata']['page'],2);self.assertTrue(pdf['image'].startswith('data:image/png'))
        media=self.client.call('preview',{'path':str(self.video),'play':True});self.assertEqual(media['mediaKind'],'video');self.assertTrue(media['media'].startswith('data:video/mp4'))
        import base64
        sample=self.dir/'sample.mp4';sample.parent.mkdir(exist_ok=True);sample.write_bytes(base64.b64decode(media['media'].split(',')[1]));self.assertGreater(float(probe(sample,self.engines['ffprobe'])['format']['duration']),.5)
        audio=self.dir/'sample.wav';command([self.engines['ffmpeg'],'-v','error','-i',self.video,'-vn',audio])
        result=self.client.call('preview',{'path':str(audio),'play':True});self.assertEqual(result['mediaKind'],'audio');self.assertTrue(result['media'].startswith('data:audio/mp4'))
        from docx import Document
        doc=Document();doc.add_paragraph('Office preview actual content');file=self.dir/'preview.docx';doc.save(file)
        result=self.client.call('preview',{'path':str(file)});self.assertGreater(result['metadata']['pages'],0);self.assertTrue(result['image'])
    def test_shell_paths_only_and_matrix(self):
        from context_menu import keys
        verbs=keys(self.engines)
        for path,_,target in verbs:
            self.assertTrue(path.startswith('Software\\Classes\\*\\shell\\FileConverter') or path.startswith('Software\\Classes\\SystemFileAssociations\\.') and '\\shell\\FileConverterTo' in path)
            self.assertNotIn('DefaultIcon',path);self.assertNotIn('OpenWith',path)
        names=[p for p,_,_ in verbs];self.assertTrue(any('.docx\\shell\\FileConverterToPDF' in p for p in names));self.assertFalse(any('.pdf\\shell\\FileConverterToMP3' in p for p in names))

if __name__=='__main__':unittest.main(verbosity=2)
