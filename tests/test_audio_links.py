"""Real delayed audio, split project metadata, no duplicate sound and mute/mix samples."""
from pathlib import Path
import sys,tempfile,unittest,copy,array,math
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'engine'),str(ROOT/'tests')]
from runtime import locate,command
from test_engine import Client
from editors import inspect
class LinkedAudioTests(unittest.TestCase):
 def test_delay_mute_mix_legacy_and_project_roundtrip(self):
  e=locate(ROOT/'vendor')
  with tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='linked-audio-') as scratch:
   root=Path(scratch);source=root/'延遲 & source.mp4'
   command([e['ffmpeg'],'-v','error','-f','lavfi','-i','color=red:s=160x90:r=20:d=3','-itsoffset','0.5','-f','lavfi','-i','sine=f=440:d=2','-c:v','libx264','-preset','ultrafast','-c:a','aac',source])
   metadata=inspect(source,e);self.assertTrue(metadata['hasAudio']);self.assertGreater(metadata['audioStart'],.4);self.assertTrue(metadata['waveform'])
   client=Client(root/'data')
   def render(clips):
    p={'type':'fcvideo','version':1,'width':160,'height':90,'fps':20,'clips':clips,'export':{'hardware':'cpu'}}
    saved=client.call('editor',{'action':'save','type':'fcvideo','path':str(root/'roundtrip.fcvideo.json'),'project':p})
    p=client.call('editor',{'action':'load','type':'fcvideo','path':saved['path']})['project']
    job=client.call('editor',{'action':'enqueue','type':'fcvideo','project':p,'format':'wav','outputDir':str(root/'out')})
    result=client.wait([job['id']],timeout=40)[0];self.assertEqual(result['status'],'completed',result.get('error'))
    values=array.array('f');values.frombytes(command([e['ffmpeg'],'-v','error','-i',result['outputs'][0],'-ar','48000','-ac','1','-f','f32le','-']))
    return values,p
   def rms(samples,start,end):
    chunk=samples[int(start*48000):int(end*48000)];return math.sqrt(sum(v*v for v in chunk)/len(chunk))
   try:
    v={'id':'v','source':str(source),'track':'V1','at':0,'in':0,'out':3}
    old,_=render([v]);visual=dict(v,pairId='pair',linked=True,videoOnly=True,mute=False)
    audio=dict(v,id='a',track='A1',pairId='pair',linked=True)
    new,project=render([visual,audio]);self.assertTrue(project['clips'][0]['videoOnly']);self.assertEqual(project['clips'][1]['pairId'],'pair')
    self.assertLess(rms(new,.05,.3),.002);self.assertGreater(rms(new,.8,1.2),.02)
    self.assertAlmostEqual(rms(old,.8,1.2),rms(new,.8,1.2),delta=.002)
    muted,_=render([visual,dict(audio,mute=True)]);self.assertLess(rms(muted,.8,1.2),.001)
    music,_=render([visual,dict(audio,mute=True),dict(audio,id='music',track='A2',pairId='',linked=False,volume=.5)])
    self.assertAlmostEqual(rms(music,.8,1.2)/rms(new,.8,1.2),.5,delta=.04)
    cut,_=render([dict(visual,**{'in':1,'out':2}),dict(audio,**{'in':1,'out':2})]);self.assertGreater(rms(cut,.1,.3),.02)
   finally:client.close()
