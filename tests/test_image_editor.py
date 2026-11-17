"""Real layered raster exports, alpha, project persistence and non-destructive filters."""
import sys,unittest,tempfile,hashlib,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'engine'),str(ROOT/'tests')]
from test_engine import Client
from PIL import Image,ImageDraw
class ImageEditorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'.tools',prefix='image-editor-');self.root=Path(self.temp.name);self.client=Client(self.root/'data')
  self.source=self.root/'原圖 & alpha.png';im=Image.new('RGBA',(100,80));ImageDraw.Draw(im).rectangle((10,10,89,69),fill='red');im.save(self.source);self.sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
 def tearDown(self):
  self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.sha);self.client.close()
  from fsutils import remove_tree
  remove_tree(self.root,ROOT/'.tools');self.temp.cleanup()
 def layer(self,type,**kw):return dict(id=uuid.uuid4().hex,type=type,**kw)
 def project(self,layers,**kw):return dict(type='fcimage',version=1,width=100,height=80,layers=layers,**kw)
 def output(self,p,fmt='png'):
  job=self.client.call('editor',{'action':'enqueue','type':'fcimage','project':p,'format':fmt,'outputDir':str(self.root/'out')});state=self.client.wait([job['id']])[0];self.assertEqual(state['status'],'completed',state.get('error'));
  with Image.open(state['outputs'][0]) as result:return result.copy()
 def test_layers_order_visibility_alpha_crop_and_all_exports(self):
  base=self.layer('image',source=str(self.source),width=100,height=80);blue=self.layer('rect',x=20,y=20,width=30,height=20,color='blue')
  p=self.project([base,blue]);im=self.output(p);self.assertEqual(im.getpixel((25,25)),(0,0,255,255));self.assertEqual(im.getpixel((0,0))[3],0)
  p['layers']=[blue,base];im=self.output(p);self.assertEqual(im.getpixel((25,25)),(255,0,0,255))
  base['visible']=False;im=self.output(p);self.assertEqual(im.getpixel((70,50))[3],0)
  base['visible']=True;p['crop']=[10,10,60,40];p['outputWidth']=300;p['outputHeight']=200
  for fmt in ['png','jpg','webp']:
   im=self.output(p,fmt);self.assertEqual(im.size,(300,200));self.assertIn(im.mode,['RGB','RGBA'])
 def test_filters_rotation_brush_eraser_mosaic_and_project_roundtrip(self):
  base=self.layer('image',source=str(self.source),width=80,height=100,rotation=90,flipH=True,brightness=.5,contrast=1.2,saturation=0,warmth=.2,blur=.2,sharpen=1,filter='sepia')
  brush=self.layer('brush',points=[[10,10],[50,10]],stroke=6,color='blue');eraser=self.layer('eraser',points=[[20,10],[25,10]],stroke=8)
  text=self.layer('text',text='中文',fontSize=14,width=60,height=20,x=0,y=50,color='white')
  mosaic=self.layer('mosaic',x=40,y=20,width=30,height=30,mosaicSize=10)
  p=self.project([base,brush,eraser,text,mosaic]);im=self.output(p);self.assertEqual(im.getpixel((22,10))[3],0);self.assertEqual(im.getpixel((40,10))[:3],(0,0,255))
  path=self.root/'中文.fcimage.json';self.client.call('editor',{'action':'save','type':'fcimage','path':str(path),'project':p});loaded=self.client.call('editor',{'action':'load','type':'fcimage','path':str(path)})['project'];self.assertEqual(len(loaded['layers']),5);self.assertEqual(loaded['layers'][1]['points'],[[10,10],[50,10]])
  again=self.output(loaded);self.assertEqual(im.tobytes(),again.tobytes())
 def test_mosaic_changes_actual_pixels(self):
  checker=self.root/'checker.png';image=Image.new('RGBA',(100,80))
  for y in range(80):
   for x in range(100):image.putpixel((x,y),(255,255,255,255) if (x+y)%2 else (0,0,0,255))
  image.save(checker);p=self.project([self.layer('image',source=str(checker),width=100,height=80),self.layer('mosaic',x=10,y=10,width=40,height=40,mosaicSize=10)])
  result=self.output(p);self.assertEqual(result.getpixel((20,20)),result.getpixel((21,20)));self.assertNotEqual(result.getpixel((2,2)),result.getpixel((3,2)))
 def test_validation_and_source_write_protection(self):
  p=self.project([self.layer('image',source=str(self.source),width=100,height=80)]);p['crop']=[90,0,30,10]
  with self.assertRaises(ValueError):self.output(p)
  p['crop']=[0,0,100,80]
  with self.assertRaises(ValueError):self.client.call('editor',{'action':'save','type':'fcimage','path':str(self.source),'project':p})
if __name__=='__main__':unittest.main(verbosity=2)
