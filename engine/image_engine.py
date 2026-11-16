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
            width=int(number(opt,'width',0,0,100000));height=int(number(opt,'height',0,0,100000))
            if width or height:
                if not width:width=max(1,round(image.width*height/image.height))
                if not height:height=max(1,round(image.height*width/image.width))
                image=image.resize((width,height),Image.Resampling.LANCZOS)
            if fmt in {'jpg','bmp'}:
                base=Image.new('RGB',image.size,str(opt.get('matte','#ffffff')));base.paste(image,mask=image.getchannel('A'));image=base
            frames.append(image);durations.append(frame.info.get('duration',100))
        target=stage/(sources[0].stem+'.'+fmt)
        extra={'quality':int(number(opt,'quality',90,1,100))}
        if len(frames)>1:extra.update(save_all=True,append_images=frames[1:],duration=durations,loop=source.info.get('loop',0))
        frames[0].save(target,format={'jpg':'JPEG','tiff':'TIFF','heic':'HEIF'}.get(fmt,fmt.upper()),**extra)
    return [target]
