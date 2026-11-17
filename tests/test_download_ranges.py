"""Real range downloads of owned HTTP media, plus metadata boundary validation."""
import sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine'),str(ROOT/'tests')]
import test_p3 as fixtures
from downloads import execute,sections,selected,ANALYSES
from worker import probe

class RangeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixtures.P3Tests.setUpClass();cls.engines=fixtures.P3Tests.engines
 @classmethod
 def tearDownClass(cls):fixtures.P3Tests.tearDownClass()
 def test_boundaries_and_untrusted_request(self):
  for value,length in [([{'start':-1,'end':1}],2),([{'start':1,'end':1}],2),([{'start':0,'end':3}],2),([{'start':0,'end':1}],None),([{'start':0,'end':float('inf')}],2),([{'start':float('nan'),'end':1}],2)]:
   with self.assertRaises(ValueError):sections(value,length)
  entry={'url':fixtures.P3Tests.base+'720.mp4','title':'Owned','id':'one','duration':2,'formats':[],'subtitles':[]}
  ANALYSES['owned']={'entries':{'1':entry}}
  try:
   result=selected('owned',[{'key':'1','sections':[{'start':.25,'end':1.25}],'precise':True}])[0]
   self.assertEqual(result['sections'],[{'start':.25,'end':1.25}]);self.assertTrue(result['precise'])
   with self.assertRaises(ValueError):selected('owned',[{'key':'1','sections':[{'start':0,'end':3}]}])
  finally:ANALYSES.pop('owned',None)
 def download(self,root,parts,precise=True,audio=False,merge=False,convert=''):
  stage=root/'stage';stage.mkdir();job={'downloadCache':str(root/'cache'),'options':{'hardware':'cpu'},'download':{'url':fixtures.P3Tests.base+'720.mp4','duration':2,'entryId':'720','title':'Owned','formatId':'best','audioOnly':audio,'audioFormat':'flac','sections':parts,'precise':precise,'mergeSections':merge,'convertTo':convert}}
  return execute(job,stage,self.engines)
 def test_precise_non_keyframe_duration_and_separate_transcode(self):
  with tempfile.TemporaryDirectory(dir=fixtures.P3Tests.root) as folder:
   outputs=self.download(Path(folder),[{'start':.25,'end':1.25},{'start':1.25,'end':1.75}],convert='mp4')
   self.assertEqual(len(outputs),2)
   for file,expected in zip(outputs,[1,.5]):
    info=probe(file,self.engines['ffprobe']);self.assertAlmostEqual(float(info['format']['duration']),expected,delta=.16)
 def test_fast_and_merged_audio(self):
  for precise,audio,merge in [(False,False,False),(True,True,True),(True,False,True)]:
   with tempfile.TemporaryDirectory(dir=fixtures.P3Tests.root) as folder:
    outputs=self.download(Path(folder),[{'start':0,'end':.75},{'start':1,'end':1.75}],precise,audio,merge)
    self.assertEqual(len(outputs),1 if merge else 2)
    for file in outputs:
     info=probe(file,self.engines['ffprobe']);self.assertGreater(float(info['format']['duration']),0)
     if audio:self.assertEqual(info['streams'][0]['codec_type'],'audio')
if __name__=='__main__':unittest.main(verbosity=2)
