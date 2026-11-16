"""Real yt-dlp tests against only owned, locally served media (no third-party sites)."""
from pathlib import Path
import functools
import http.server
import json
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,command
from worker import probe
from test_engine import Client
from PIL import Image

class P3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='p3-');cls.root=Path(cls.temp.name);cls.engines=locate(ROOT/'vendor');cls.ranges=[]
        for label,width,height in [('720',1280,720),('1080',1920,1080)]:
            video=cls.root/(label+'.mp4')
            command([cls.engines['ffmpeg'],'-v','error','-f','lavfi','-i',f'testsrc2=s={width}x{height}:r=12:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-preset','ultrafast','-c:a','aac','-movflags','+faststart','-shortest',video])
            command([cls.engines['ffmpeg'],'-v','error','-i',video,'-c','copy','-hls_time','1','-hls_list_size','0','-hls_segment_filename',cls.root/(label+'-%03d.ts'),cls.root/(label+'.m3u8')])
        (cls.root/'master.m3u8').write_text('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720,CODECS="avc1.42c01f,mp4a.40.2"\n720.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,CODECS="avc1.42c028,mp4a.40.2"\n1080.m3u8\n')
        (cls.root/'en.vtt').write_text('WEBVTT\n\n00:00.000 --> 00:01.500\nOwned legal subtitle\n')
        Image.new('RGB',(160,90),'#4477aa').save(cls.root/'poster.png')
        html='<!doctype html><html><head><title>Owned playlist</title></head><body>'
        for i,label in enumerate(['720','1080']):html+=f'<video id="owned-{i}" title="Owned video {i+1}" poster="poster.png" controls><source src="{label}.mp4" type="video/mp4"><track kind="subtitles" src="en.vtt" srclang="en" label="English"></video>'
        (cls.root/'playlist.html').write_text(html+'</body></html>')
        shutil.copy2(cls.root/'1080.mp4',cls.root/'slow.mp4')
        owner=cls
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                path=Path(self.translate_path(self.path))
                if path.suffix.lower()=='.mp4' and path.is_file():
                    size=path.stat().st_size;start=0;stop=size-1;header=self.headers.get('Range')
                    if header:
                        match=re.match(r'bytes=(\d+)-(\d*)',header)
                        if match:start=int(match[1]);stop=min(stop,int(match[2])) if match[2] else stop
                        owner.ranges.append((path.name,start))
                    if start>=size:self.send_error(416);return
                    self.send_response(206 if header else 200);self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(stop-start+1))
                    if header:self.send_header('Content-Range',f'bytes {start}-{stop}/{size}')
                    self.end_headers()
                    try:
                        with path.open('rb') as source:
                            source.seek(start);remaining=stop-start+1
                            while remaining:
                                block=source.read(min(16384,remaining))
                                if not block:break
                                self.wfile.write(block);self.wfile.flush();remaining-=len(block)
                                if path.name=='slow.mp4':time.sleep(.04)
                    except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
                else:super().do_GET()
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(cls.root)))
        cls.server.daemon_threads=True;threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.base=f'http://127.0.0.1:{cls.server.server_port}/'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()
        from fsutils import remove_tree
        remove_tree(cls.root,ROOT/'.tools');cls.temp.cleanup()
    def setUp(self):
        import uuid
        self.dir=self.root/uuid.uuid4().hex;self.client=Client(self.dir/'data');self.out=self.dir/'下載 & output'
    def tearDown(self):self.client.close()
    def start(self,analysis,item):return self.client.call('enqueue_download',{'analysisId':analysis['analysisId'],'items':[item],'outputDir':str(self.out)})[0]
    def complete(self,job,timeout=60):
        result=self.client.wait([job['id']],timeout=timeout)[0];self.assertEqual(result['status'],'completed',result.get('error'));return result
    def test_actual_quality_parse_download_and_transcode(self):
        analysis=self.client.call('analyze_url',{'url':self.base+'master.m3u8'});entry=analysis['entries'][0]
        heights={f.get('height') for f in entry['formats']};self.assertIn(720,heights);self.assertIn(1080,heights);self.assertNotIn(2160,heights)
        choice=next(f['format_id'] for f in entry['formats'] if f.get('height')==720)
        job=self.complete(self.start(analysis,{'key':entry['key'],'formatId':choice,'convertTo':'mp4'}))
        video=next(p for p in job['outputs'] if Path(p).suffix=='.mp4');self.assertEqual(probe(video,self.engines['ffprobe'])['streams'][0]['height'],720)
        self.assertGreater(job['stats']['downloadedBytes'],0);self.assertFalse(Path(job['downloadCache']).exists())
    def test_playlist_selection_audio_and_subtitles(self):
        analysis=self.client.call('analyze_url',{'url':self.base+'playlist.html'});self.assertTrue(analysis['playlist']);self.assertEqual(len(analysis['entries']),2)
        entry=analysis['entries'][1]
        resolved=self.client.call('resolve_download',{'analysisId':analysis['analysisId'],'key':entry['key']})
        self.assertIn('en',resolved['subtitles'])
        job=self.complete(self.start(analysis,{'key':entry['key'],'audioOnly':True,'audioFormat':'flac','subtitles':['en']}))
        audio=next(p for p in job['outputs'] if Path(p).suffix=='.flac');self.assertEqual(probe(audio,self.engines['ffprobe'])['streams'][0]['codec_name'],'flac')
        captions=[Path(p) for p in job['outputs'] if Path(p).suffix in {'.vtt','.srt'}];self.assertTrue(captions);self.assertIn('Owned legal subtitle',captions[0].read_text(encoding='utf-8-sig'))
        self.assertEqual(sum(Path(p).suffix=='.flac' for p in job['outputs']),1)
    def test_audio_postprocess_formats(self):
        analysis=self.client.call('analyze_url',{'url':self.base+'720.mp4'});entry=analysis['entries'][0]
        for fmt,codec in [('mp3','mp3'),('m4a','aac'),('wav','pcm_s16le')]:
            job=self.complete(self.start(analysis,{'key':entry['key'],'audioOnly':True,'audioFormat':fmt}))
            path=next(p for p in job['outputs'] if Path(p).suffix=='.'+fmt)
            self.assertEqual(probe(path,self.engines['ffprobe'])['streams'][0]['codec_name'],codec)
    def test_cancel_resume_and_local_independence(self):
        analysis=self.client.call('analyze_url',{'url':self.base+'slow.mp4'});entry=analysis['entries'][0]
        job=self.start(analysis,{'key':entry['key']});deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=next(j for j in self.client.call('snapshot')['jobs'] if j['id']==job['id'])
            if state.get('stats',{}).get('downloadedBytes',0)>32768:break
            time.sleep(.1)
        self.client.call('cancel',{'id':job['id']});cancelled=self.client.wait([job['id']])[0];self.assertEqual(cancelled['status'],'cancelled')
        self.assertTrue(any(Path(job['downloadCache']).glob('*.part')))
        # The local queue still works after a cancelled network operation.
        image=self.dir/'local.png';Image.new('RGB',(40,30),'red').save(image)
        local=self.client.call('enqueue',{'jobs':[{'sources':[str(image)],'format':'webp','outputDir':str(self.out)}]})[0]
        self.assertEqual(self.client.wait([local['id']])[0]['status'],'completed')
        resumed=self.client.call('retry',{'id':job['id']})[0];self.complete(resumed)
        self.assertTrue(any(name=='slow.mp4' and offset>0 for name,offset in self.ranges))
    def test_no_credentials_or_non_http(self):
        for url in ['file:///C:/Windows/win.ini','https://user:password@example.com/video']:
            with self.assertRaises(ValueError):self.client.call('analyze_url',{'url':url})
        from downloads import settings
        options=settings(self.engines);self.assertIsNone(options['cookiesfrombrowser']);self.assertIsNone(options['cookiefile']);self.assertFalse(options['remote_components'])

if __name__=='__main__':unittest.main(verbosity=2)
