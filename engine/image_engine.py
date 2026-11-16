"""Pillow/HEIF image pipeline; preserve animation only in animation-capable targets."""
from PIL import Image,ImageOps,ImageSequence
from runtime import image_plugins

def convert_image(job,sources,stage,engines):
    from worker import number
    image_plugins();opt=job.get('options',{});fmt=job['format']
    with Image.open(sources[0]) as source:
        frames=[];durations=[]
        sequence=ImageSequence.Iterator(source) if fmt in {'gif','webp'} else [source]
        for frame in sequence:
            image=ImageOps.exif_transpose(frame.copy()).convert('RGBA')
            image=process_frame(image,job,engines)
            width=int(number(opt,'width',0,0,100000));height=int(number(opt,'height',0,0,100000))
            if width or height:
                if not width:width=max(1,round(image.width*height/image.height))
                if not height:height=max(1,round(image.height*width/image.width))
                image=image.resize((width,height),Image.Resampling.LANCZOS)
            if fmt in {'jpg','bmp'}:
                base=Image.new('RGB',image.size,str(opt.get('matte','#ffffff')));base.paste(image,mask=image.getchannel('A'));image=base
            frames.append(image);durations.append(frame.info.get('duration',100))
        target=stage/(sources[0].stem+'.'+fmt)
        if job.get('operation')=='image.strip-metadata':
            for frame in frames:frame.info.clear()
        extra={'optimize':True,'quality':int(number(opt,'quality',90,1,100))}
        if len(frames)>1:extra.update(save_all=True,append_images=frames[1:],duration=durations,loop=source.info.get('loop',0))
        frames[0].save(target,format={'jpg':'JPEG','tiff':'TIFF','heic':'HEIF'}.get(fmt,fmt.upper()),**extra)
    return [target]

def box(image,value):
    x,y,w,h=value
    left=max(0,int(x*image.width));top=max(0,int(y*image.height))
    return left,top,min(image.width,max(left+1,round((x+w)*image.width))),min(image.height,max(top+1,round((y+h)*image.height)))

def process_frame(image,job,engines):
    from PIL import ImageDraw,ImageFont,ImageColor
    from pathlib import Path
    op=job.get('operation','');p=job.get('params',{})
    if op=='image.crop':image=image.crop(box(image,p['region']))
    elif op=='image.rotate':image=image.rotate(-int(p['angle']),expand=True)
    elif op=='image.watermark':
        if not p['text'].strip():raise ValueError('請輸入浮水印文字')
        rect=box(image,p['region']);overlay=Image.new('RGBA',image.size)
        draw=ImageDraw.Draw(overlay);fontpath=engines.get('font') or 'C:/Windows/Fonts/msjh.ttc'
        size=int(p['fontSize']);font=ImageFont.truetype(fontpath,size) if Path(fontpath).exists() else ImageFont.load_default(size=size)
        bounds=draw.textbbox((0,0),p['text'],font=font)
        factor=min(1,(rect[2]-rect[0])/max(1,bounds[2]-bounds[0]),(rect[3]-rect[1])/max(1,bounds[3]-bounds[1]))
        if factor<1:
            size=max(4,int(size*factor));font=ImageFont.truetype(fontpath,size) if Path(fontpath).exists() else ImageFont.load_default(size=size)
        color=ImageColor.getrgb(p['color'])+(round(p['opacity']*255),)
        draw.text((rect[0],rect[1]),p['text'],font=font,fill=color)
        image=Image.alpha_composite(image,overlay)
    elif op=='image.repair':
        import cv2,numpy as np
        array=cv2.cvtColor(np.array(image.convert('RGB')),cv2.COLOR_RGB2BGR)
        mask=np.zeros(array.shape[:2],dtype=np.uint8);left,top,right,bottom=box(image,p['region']);mask[top:bottom,left:right]=255
        repaired=cv2.inpaint(array,mask,float(p['radius']),cv2.INPAINT_TELEA)
        image=Image.fromarray(cv2.cvtColor(repaired,cv2.COLOR_BGR2RGB)).convert('RGBA')
    return image

def execute_tool(job,sources,stage,engines):
    from fsutils import publish_file
    from worker import emit
    p=job['params'];fmt=p.get('format','png');results=[]
    for i,source in enumerate(sources):
        work=stage/('.image-'+str(i));work.mkdir()
        options={**job.get('options',{}),**p};local=dict(job,format=fmt,options=options)
        output=convert_image(local,[source],work,engines)[0]
        budget=float(p.get('targetMB',0))*1024*1024
        if job['operation']=='image.compress' and budget and output.stat().st_size>budget and fmt!='png':
            low=int(p['minQuality']);high=max(low,int(p.get('quality',90)));best=None
            for attempt in range(8):
                quality=(low+high)//2;local['options']['quality']=quality
                candidate=convert_image(local,[source],work,engines)[0]
                if candidate.stat().st_size<=budget:best=candidate.read_bytes();low=quality+1
                else:high=quality-1
                if low>high:break
            if best is not None:output.write_bytes(best)
            else:
                local['options']['quality']=int(p['minQuality']);output=convert_image(local,[source],work,engines)[0]
        if budget and output.stat().st_size>budget:
            emit(stats={'warning':'無法在所選最低品質內達到目標大小，已輸出可行結果','targetMet':False})
        elif budget:emit(stats={'targetMet':True})
        results.append(publish_file(output,stage));emit((i+1)/len(sources)*95)
    return results
