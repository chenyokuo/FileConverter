"""Real owned HLS → queued local H264 preview; no mock completion or public dependency."""
from pathlib import Path
import tempfile,unittest
import test_p3 as fixtures
import time
from test_engine import Client
from worker import probe
class DownloadPreviewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):fixtures.P3Tests.setUpClass()
 @classmethod
 def tearDownClass(cls):fixtures.P3Tests.tearDownClass()
 def test_local_preview_queue_codec_scope_cleanup_and_download_independence(self):
  with tempfile.TemporaryDirectory(dir=fixtures.P3Tests.root) as folder:
   root=Path(folder);client=Client(root/'data')
   try:
    analysis=client.call('analyze_url',{'url':fixtures.P3Tests.base+'master.m3u8'})
    job=client.call('download_preview',{'analysisId':analysis['analysisId'],'key':analysis['entries'][0]['key']})
    
    for _ in range(400):
     result=client.call('preview_status',{'id':job['id']})
     if result['status'] in {'completed','failed','cancelled'}:break
     time.sleep(.1)
    self.assertEqual(result['status'],'completed',result.get('error'))
    self.assertTrue(result['previewOnly']);self.assertTrue(Path(result['outputs'][0]).is_relative_to(root/'data/previews'))
    metadata=probe(Path(result['outputs'][0]),fixtures.P3Tests.engines['ffprobe']);video=next(s for s in metadata['streams'] if s['codec_type']=='video')
    self.assertEqual(video['codec_name'],'h264');self.assertEqual(video['height'],360);self.assertAlmostEqual(float(metadata['format']['duration']),2,delta=.2)
    self.assertEqual(client.call('snapshot')['jobs'],[])
    client.call('clear_preview',{'id':job['id']});self.assertFalse(Path(result['outputDir']).exists());self.assertFalse(Path(result['downloadCache']).exists())
    with self.assertRaises(ValueError):client.call('download_preview',{'analysisId':'expired','key':'1'})
    normal=client.call('enqueue_download',{'analysisId':analysis['analysisId'],'items':[{'key':analysis['entries'][0]['key'],'sections':[{'start':.25,'end':1.25}],'precise':True}],'outputDir':str(root/'normal')})[0]
    result=client.wait([normal['id']])[0];self.assertEqual(result['status'],'completed',result.get('error'));self.assertAlmostEqual(float(probe(Path(result['outputs'][0]),fixtures.P3Tests.engines['ffprobe'])['format']['duration']),1,delta=.2)
   finally:client.close()
