"""EXIF display dimensions must agree with the editor's oriented pixels and export."""
from pathlib import Path
import hashlib,tempfile,unittest
from PIL import Image,ImageDraw
from test_engine import Client
ROOT=Path(__file__).resolve().parents[1]
class EditorOrientationTests(unittest.TestCase):
 def test_oriented_import_outputs_and_legacy_project_dimensions(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='editor-orientation-') as folder:
   root=Path(folder);source=root/'旋轉 & original.jpg';image=Image.new('RGB',(1255,893),'white');draw=ImageDraw.Draw(image);draw.rectangle((0,0,99,99),fill='red');draw.rectangle((1155,793,1254,892),fill='blue');exif=Image.Exif();exif[274]=6;image.save(source,quality=98,exif=exif);original=hashlib.sha256(source.read_bytes()).hexdigest();client=Client(root/'data')
   try:
    info=client.call('editor',{'action':'inspect','path':str(source)});self.assertEqual((info['width'],info['height']),(893,1255))
    project={'type':'fcimage','version':1,'width':893,'height':1255,'crop':[0,0,893,1255],'layers':[{'id':'photo','type':'image','source':str(source),'width':893,'height':1255}]}
    for format in ['png','jpg','webp']:
     job=client.call('editor',{'action':'enqueue','type':'fcimage','project':project,'format':format,'outputDir':str(root/'out')});result=client.wait([job['id']])[0];self.assertEqual(result['status'],'completed',result.get('error'))
     with Image.open(result['outputs'][0]) as output:
      output.load();self.assertEqual(output.size,(893,1255));self.assertGreater(output.getpixel((843,50))[0],200);self.assertGreater(output.getpixel((50,1205))[2],200)
    legacy=dict(project,width=1255,height=893,crop=[0,0,1255,893],layers=[dict(project['layers'][0],width=1255,height=893)])
    saved=client.call('editor',{'action':'save','type':'fcimage','project':legacy,'path':str(root/'legacy.fcimage.json')});loaded=client.call('editor',{'action':'load','type':'fcimage','path':saved['path']})['project'];self.assertEqual((loaded['width'],loaded['height']),(1255,893));self.assertEqual(loaded['layers'][0]['width'],1255)
    self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)
   finally:client.close()
