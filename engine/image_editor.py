"""Layer-based raster editor using app-local Pillow; no destructive source writes."""
from pathlib import Path
import math
from PIL import Image,ImageDraw,ImageFont,ImageEnhance,ImageFilter,ImageOps,ImageColor
from video_editor import number

def validate(project,check_sources=True):
 if project.get('type')!='fcimage' or project.get('version')!=1:raise ValueError('不支援的圖片專案版本')
 p={'type':'fcimage','version':1,'width':int(number(project.get('width',1024),1,32768,'畫布寬度')),'height':int(number(project.get('height',768),1,32768,'畫布高度')),'layers':[]}
 for key in ['outputWidth','outputHeight']:p[key]=int(number(project.get(key,0),0,32768,key))
 p['quality']=int(number(project.get('quality',90),1,100,'品質'));p['matte']=str(project.get('matte','white'));ImageColor.getcolor(p['matte'],'RGBA')
 crop=project.get('crop') or [0,0,p['width'],p['height']]
 if len(crop)!=4:raise ValueError('無效裁切區域')
 x,y,w,h=[number(v,0,32768,'裁切') for v in crop]
 if w<1 or h<1 or x+w>p['width'] or y+h>p['height']:raise ValueError('裁切超出畫布')
 p['crop']=[x,y,w,h];ids=set()
 if len(project.get('layers',[]))>1000:raise ValueError('單一專案最多 1000 圖層')
 for raw in project.get('layers',[]):
  l={'id':str(raw['id']),'type':raw['type'],'name':str(raw.get('name','圖層'))[:200],'visible':bool(raw.get('visible',True)),'flipH':bool(raw.get('flipH')),'flipV':bool(raw.get('flipV'))}
  if l['id'] in ids:raise ValueError('圖層 ID 重複')
  ids.add(l['id'])
  if l['type'] not in {'image','text','rect','ellipse','brush','eraser','mosaic'}:raise ValueError('未知圖層類型')
  for key,default,low,high in [('x',0,-32768,32768),('y',0,-32768,32768),('width',100,1,32768),('height',100,1,32768),('rotation',0,0,270),('opacity',1,0,1),('brightness',1,0,3),('contrast',1,0,3),('saturation',1,0,3),('warmth',0,-1,1),('blur',0,0,100),('sharpen',0,0,5),('fontSize',40,4,1000),('stroke',8,1,1000),('mosaicSize',12,2,200)]:l[key]=number(raw.get(key,default),low,high,key)
  if l['rotation'] not in {0,90,180,270}:raise ValueError('旋轉角度須為 0/90/180/270')
  l['filter']=raw.get('filter','none')
  if l['filter'] not in {'none','grayscale','sepia'}:raise ValueError('未知濾鏡')
  l['color']=str(raw.get('color','white'));ImageColor.getcolor(l['color'],'RGBA');l['text']=str(raw.get('text',''))
  if len(l['text'])>10000:raise ValueError('文字過長')
  l['points']=[]
  if len(raw.get('points',[]))>100000:raise ValueError('筆畫節點過多')
  for point in raw.get('points',[]):
   if len(point)!=2:raise ValueError('無效筆畫')
   l['points'].append([number(v,-32768,32768,'筆畫座標') for v in point])
  if l['type']=='image':
   path=Path(raw['source']).resolve();l['source']=str(path)
   if check_sources:
    if not path.is_file():raise ValueError('遺失素材：'+str(path))
    with Image.open(path) as image:image.verify()
  p['layers'].append(l)
 return p

def paint(p,engines):
 base=Image.new('RGBA',(p['width'],p['height']))
 for l in p['layers']:
  if not l['visible']:continue
  x,y=round(l['x']),round(l['y']);w,h=max(1,round(l['width'])),max(1,round(l['height']))
  if l['type'] in {'brush','eraser'}:
   points=[(v[0]+x,v[1]+y) for v in l['points']]
   if not points:continue
   mask=Image.new('L',base.size,0);draw=ImageDraw.Draw(mask);stroke=round(l['stroke']);draw.line(points,fill=round(255*l['opacity']),width=stroke,joint='curve')
   for px,py in points:draw.ellipse((px-stroke/2,py-stroke/2,px+stroke/2,py+stroke/2),fill=round(255*l['opacity']))
   if l['type']=='eraser':
    import PIL.ImageChops as chops
    base.putalpha(chops.multiply(base.getchannel('A'),ImageOps.invert(mask)))
   else:base.alpha_composite(Image.composite(Image.new('RGBA',base.size,l['color']),Image.new('RGBA',base.size),mask))
   continue
  if l['type']=='mosaic':
   box=(max(0,x),max(0,y),min(base.width,x+w),min(base.height,y+h))
   if box[2]>box[0] and box[3]>box[1]:
    part=base.crop(box);part=part.resize((max(1,part.width//round(l['mosaicSize'])),max(1,part.height//round(l['mosaicSize']))),Image.Resampling.BOX).resize(part.size,Image.Resampling.NEAREST);base.paste(Image.blend(base.crop(box),part,l['opacity']),box)
   continue
  if l['type']=='image':
   with Image.open(l['source']) as source:layer=ImageOps.exif_transpose(source).convert('RGBA')
   if l['flipH']:layer=ImageOps.mirror(layer)
   if l['flipV']:layer=ImageOps.flip(layer)
   if l['rotation']:layer=layer.rotate(-l['rotation'],expand=True)
   layer=layer.resize((w,h),Image.Resampling.LANCZOS);alpha=layer.getchannel('A');rgb=layer.convert('RGB')
   rgb=ImageEnhance.Brightness(rgb).enhance(l['brightness']);rgb=ImageEnhance.Contrast(rgb).enhance(l['contrast']);rgb=ImageEnhance.Color(rgb).enhance(l['saturation'])
   if l['warmth']:
    r,g,b=rgb.split();r=r.point(lambda v:min(255,max(0,round(v+40*l['warmth']))));b=b.point(lambda v:min(255,max(0,round(v-40*l['warmth']))));rgb=Image.merge('RGB',(r,g,b))
   if l['filter']=='grayscale':rgb=ImageOps.grayscale(rgb).convert('RGB')
   if l['filter']=='sepia':rgb=ImageOps.colorize(ImageOps.grayscale(rgb),'#352515','#f2dfb0').convert('RGB')
   layer=rgb.convert('RGBA');layer.putalpha(alpha)
   if l['blur']:layer=layer.filter(ImageFilter.GaussianBlur(l['blur']))
   if l['sharpen']:layer=layer.filter(ImageFilter.UnsharpMask(radius=2,percent=round(l['sharpen']*100),threshold=3))
  else:
   layer=Image.new('RGBA',(w,h));draw=ImageDraw.Draw(layer)
   if l['type']=='text':
    if not engines.get('font'):raise ValueError('本機字型不存在')
    font=ImageFont.truetype(engines['font'],round(l['fontSize']));draw.multiline_text((0,0),l['text'],fill=l['color'],font=font,spacing=4)
   elif l['type']=='rect':draw.rectangle((0,0,w-1,h-1),fill=l['color'])
   elif l['type']=='ellipse':draw.ellipse((0,0,w-1,h-1),fill=l['color'])
  if l['opacity']<1:layer.putalpha(layer.getchannel('A').point(lambda v:round(v*l['opacity'])))
  base.alpha_composite(layer,(x,y))
 return base

def render(job,stage,engines):
 from worker import emit
 p=validate(job['project']);image=paint(p,engines);emit(75,stats={'phase':'圖片圖層合成'})
 if not job.get('previewOnly'):
  x,y,w,h=p['crop'];image=image.crop((round(x),round(y),round(x+w),round(y+h)))
  width=p['outputWidth'];height=p['outputHeight']
  if width or height:
   if not width:width=max(1,round(image.width*height/image.height))
   if not height:height=max(1,round(image.height*width/image.width))
   image=image.resize((width,height),Image.Resampling.LANCZOS)
 else:image.thumbnail((1400,1400),Image.Resampling.LANCZOS)
 fmt='png' if job.get('previewOnly') else job.get('format','png');target=stage/('edited.'+fmt)
 if fmt=='jpg':
  matte=Image.new('RGB',image.size,p['matte']);matte.paste(image,mask=image.getchannel('A'));image=matte
 image.save(target,format={'png':'PNG','jpg':'JPEG','webp':'WEBP'}[fmt],quality=p['quality'],**({'lossless':True} if fmt=='webp' else {}));emit(99);return [target]
