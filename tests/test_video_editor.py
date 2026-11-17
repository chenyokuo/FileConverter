"""Real multi-track timeline rendering; checks pixels, audio, duration and project IO."""
import sys,tempfile,unittest,copy,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'engine'),str(ROOT/'tests')]
from runtime import command,locate
from test_engine import Client
from worker import probe
from PIL import Image
import video_editor
class VideoEditorTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='editor-');cls.root=Path(cls.temp.name);cls.e=locate(ROOT/'vendor')
  for name,color,hz,size in [('red','red',440,'320x180'),('blue','blue',880,'240x240'),('green','green',660,'640x360')]:
   command([cls.e['ffmpeg'],'-v','error','-f','lavfi','-i',f'color=c={color}:s={size}:r=20:d=2','-f','lavfi','-i',f'sine=f={hz}:d=2','-c:v','libx264','-preset','ultrafast','-c:a','aac','-shortest',cls.root/(name+'.mp4')])
  Image.new('RGBA',(160,90),'yellow').save(cls.root/'still.png')
  cls.originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.root.iterdir() if p.is_file()}
 @classmethod
 def tearDownClass(cls):
  for p,sha in cls.originals.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
  from fsutils import remove_tree
  remove_tree(cls.root,ROOT/'.tools');cls.temp.cleanup()
 def setUp(self):self.client=Client(self.root/__import__('uuid').uuid4().hex)
 def tearDown(self):self.client.close()
 def clip(self,name,at=0,track='V1',**kw):return dict(id=__import__('uuid').uuid4().hex,source=str(self.root/(name+'.mp4')),track=track,at=at,**{'in':0,'out':2},**kw)
 def project(self,clips,**kw):return dict(type='fcvideo',version=1,width=320,height=180,fps=20,clips=clips,export={'hardware':'cpu','videoCodec':'h264','qualityPreset':'fast'},**kw)
 def enqueue(self,p,fmt='mp4',preview=False):return self.client.call('editor',{'action':'enqueue','type':'fcvideo','project':p,'format':fmt,'preview':preview,'outputDir':str(self.root/'output')})
 def finish(self,job):
  if job.get('previewOnly'):
   import time
   for _ in range(300):
    result=self.client.call('preview_status',{'id':job['id']})
    if result['status'] in {'completed','failed','cancelled'}:break
    time.sleep(.1)
  else:result=self.client.wait([job['id']],timeout=90)[0]
  self.assertEqual(result['status'],'completed',result.get('error'));return result['outputs'][0]
 def pixel(self,path,time,x=160,y=90):
  data=command([self.e['ffmpeg'],'-v','error','-ss',str(time),'-i',path,'-frames:v','1','-f','image2pipe','-vcodec','png','-'])
  import io
  return Image.open(io.BytesIO(data)).convert('RGB').getpixel((x,y))
 def test_three_sources_split_speed_gaps_and_project_roundtrip(self):
  # Split blue's source at 1s, preserving exact source/project mapping.
  red=self.clip('red');blue=self.clip('blue',2);blue['out']=1
  tail=self.clip('blue',3);tail['in']=1
  green=self.clip('green',5);green['speed']=2
  p=self.project([red,blue,tail,green]);path=self.root/'專案 中文 & .fcvideo.json'
  self.client.call('editor',{'action':'save','type':'fcvideo','path':str(path),'project':p})
  restored=self.client.call('editor',{'action':'load','type':'fcvideo','path':str(path)})['project'];self.assertEqual(len(restored['clips']),4)
  out=self.finish(self.enqueue(restored));self.assertAlmostEqual(float(probe(out,self.e['ffprobe'])['format']['duration']),6,delta=.12)
  self.assertGreater(self.pixel(out,.5)[0],220);self.assertGreater(self.pixel(out,2.5)[2],220);self.assertGreater(self.pixel(out,3.5)[2],220);self.assertLess(max(self.pixel(out,4.5)),15);self.assertGreater(self.pixel(out,5.5)[1],90)
 def test_mixing_separated_audio_dissolve_pip_titles_subtitles(self):
  red=self.clip('red');red['mute']=True;blue=self.clip('blue',1.5);blue['transition']=.5;blue['fadeOut']=.2
  original=self.clip('red',0,'A1');original['volume']=.4
  music=self.clip('green',0,'A2');music.update(volume=.3,fadeIn=.2,fadeOut=.2)
  pip=self.clip('green',.5,'V2');pip.update(size=.3,x=.65,y=.65,mute=True)
  p=self.project([red,blue,original,music,pip],titles=[{'text':'繁體 title: 100% \'test\'','start':0,'end':1,'size':20,'x':.1,'y':.1}])
  subtitle=self.root/'字幕.srt';subtitle.write_text('1\n00:00:00,100 --> 00:00:00,900\nSubtitle\n',encoding='utf-8');p['subtitles']=str(subtitle)
  out=self.finish(self.enqueue(p,'mkv'));self.assertGreater(self.pixel(out,1,250,150)[1],90)
  streams=probe(out,self.e['ffprobe'])['streams'];self.assertTrue(any(s['codec_type']=='audio' for s in streams));pixel=self.pixel(out,1.75);self.assertGreater(pixel[0],20);self.assertGreater(pixel[2],20)
  preview=self.finish(self.enqueue(p,preview=True));self.assertEqual(probe(preview,self.e['ffprobe'])['streams'][0]['width'],640)
  audio=self.finish(self.enqueue(p,'wav'));self.assertEqual(probe(audio,self.e['ffprobe'])['streams'][0]['codec_type'],'audio')
 def test_image_insertion_validation_and_missing_media(self):
  image=self.clip('red');image.update(source=str(self.root/'still.png'),**{'out':1})
  out=self.finish(self.enqueue(self.project([image]),'webm'));self.assertGreater(self.pixel(out,.3)[0],210)
  bad=self.project([self.clip('red'),self.clip('blue',1)])
  with self.assertRaises(ValueError):self.enqueue(bad)
  bad=self.project([self.clip('red')]);bad['clips'][0]['out']=3
  with self.assertRaises(ValueError):self.enqueue(bad)
  bad['clips'][0]['source']=str(self.root/'missing.mp4');path=self.root/'missing.fcvideo.json'
  self.client.call('editor',{'action':'save','type':'fcvideo','path':str(path),'project':bad})
  self.assertTrue(self.client.call('editor',{'action':'load','type':'fcvideo','path':str(path)})['missing'])
if __name__=='__main__':unittest.main(verbosity=2)
