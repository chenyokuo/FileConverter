"""Real FFmpeg progress, hardware probes and a bounded CPU fallback."""
from pathlib import Path
import subprocess
import tempfile
from runtime import FLAGS,hardware

def convert_media(job,sources,stage,engines):
    from worker import probe,emit,number
    ffmpeg=engines.get('ffmpeg');ffprobe=engines.get('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('FFmpeg Runtime 不完整')
    source=sources[0];fmt=job['format'];opt=job.get('options',{})
    info=probe(source,ffprobe);duration=float(info.get('format',{}).get('duration',0) or 0)
    audio=fmt in {'mp3','wav','flac','aac','m4a','ogg','opus'}
    codec=opt.get('videoCodec','h264');mode=opt.get('hardware','auto')
    if codec=='nvenc':mode='nvidia';codec='h264'
    if codec not in {'h264','h265','vp9'}:raise ValueError('Unknown video codec')
    if fmt=='webm':codec='vp9'
    profile=opt.get('qualityPreset','balanced')
    if profile not in {'fast','balanced','quality'}:raise ValueError('Unknown quality preset')
    selected='cpu';reason=''
    if not audio and fmt in {'mp4','mov','mkv'} and codec in {'h264','h265'} and mode!='cpu':
        devices=engines.get('hardwareCapabilities') or hardware(ffmpeg)
        available=[d['id'] for d in devices if d['id']!='cpu' and d['available'] and d.get('codecs',{}).get(codec,False)]
        if mode=='auto':selected=available[0] if available else 'cpu'
        elif mode in {'nvidia','amd','intel'}:
            selected=mode if mode in available else 'cpu'
            if selected=='cpu':reason=mode+' 不可用，改用 CPU'
        else:raise ValueError('Unknown hardware backend')
    def encoder(device):
        if audio:return {'mp3':'libmp3lame','wav':'pcm_s16le','flac':'flac','aac':'aac','m4a':'aac','ogg':'libvorbis','opus':'libopus'}[fmt]
        if fmt=='avi':return 'mpeg4'
        if fmt=='wmv':return 'wmv2'
        if codec=='vp9':return 'libvpx-vp9'
        return {'cpu':{'h264':'libx264','h265':'libx265'},'nvidia':{'h264':'h264_nvenc','h265':'hevc_nvenc'},'amd':{'h264':'h264_amf','h265':'hevc_amf'},'intel':{'h264':'h264_qsv','h265':'hevc_qsv'}}[device][codec]
    target=stage/(source.stem+'.'+fmt)
    def run(device):
        enc=encoder(device);cmd=[ffmpeg,'-hide_banner','-nostdin','-n']
        if not audio and device=='nvidia' and opt.get('hardwareDecode',True):cmd+=['-hwaccel','cuda']
        cmd+=['-i',str(source)]
        start=float(opt.get('trimStart',0));end=float(opt.get('trimEnd',0))
        if start<0 or start>=duration and duration or end and (end<=start or end>duration+.1):raise ValueError('裁切時間超出來源範圍')
        if start:cmd+=['-ss',str(start)]
        if end:cmd+=['-t',str(end-start)]
        if audio:
            cmd+=['-vn','-map','0:a:0','-c:a',enc]
            if fmt not in {'wav','flac'}:cmd+=['-b:a',str(int(number(opt,'audioBitrate',192,32,320)))+'k']
        else:
            cmd+=['-map','0:v:0','-map','0:a:0?','-c:v',enc]
            bitrate=int(number(opt,'videoBitrate',0,0,200000));crf=int(number(opt,'crf',23,0,51))
            if bitrate:cmd+=['-b:v',str(bitrate)+'k']
            elif enc in {'mpeg4','wmv2'}:cmd+=['-q:v',str({'fast':6,'balanced':4,'quality':2}[profile])]
            elif device=='cpu':cmd+=['-crf',str(crf)]+(['-b:v','0'] if codec=='vp9' else [])
            elif device=='nvidia':cmd+=['-rc','vbr','-cq',str(crf),'-b:v','0']
            elif device=='amd':cmd+=['-rc','cqp','-qp_i',str(crf),'-qp_p',str(crf)]
            else:cmd+=['-global_quality',str(crf)]
            if enc in {'libx264','libx265'}:cmd+=['-preset',{'fast':'fast','balanced':'medium','quality':'slow'}[profile]]
            elif enc=='libvpx-vp9':cmd+=['-deadline','realtime' if profile=='fast' else 'good','-cpu-used',str({'fast':6,'balanced':3,'quality':1}[profile])]
            elif device=='nvidia':cmd+=['-preset',{'fast':'p2','balanced':'p4','quality':'p6'}[profile]]
            elif device=='amd':cmd+=['-quality',{'fast':'speed','balanced':'balanced','quality':'quality'}[profile]]
            elif device=='intel':cmd+=['-preset',{'fast':'veryfast','balanced':'medium','quality':'veryslow'}[profile]]
            filters=[]
            height=int(number(opt,'videoHeight',0,0,8640))
            if height:filters+=['scale=-2:'+str(height)]
            if job.get('operation')=='video.delogo':
                stream=next(s for s in info['streams'] if s.get('codec_type')=='video')
                x,y,w,h=job['params']['region'];width,height=int(stream['width']),int(stream['height'])
                left,top,boxw,boxh=round(x*width),round(y*height),round(w*width),round(h*height)
                if left<1 or top<1 or left+boxw>=width or top+boxh>=height:raise ValueError('修補區域必須保留影片邊界')
                filters.insert(0,f'delogo=x={left}:y={top}:w={boxw}:h={boxh}')
            if filters:cmd+=['-vf',','.join(filters)]
            fps=number(opt,'fps',0,0,240)
            if fps:cmd+=['-r',str(fps)]
            cmd+=['-pix_fmt','yuv420p','-c:a','libopus' if fmt=='webm' else 'wmav2' if fmt=='wmv' else 'aac','-b:a',str(int(number(opt,'audioBitrate',192,32,320)))+'k']
        sample=int(number(opt,'sampleRate',0,0,192000));channels=int(number(opt,'channels',0,0,2))
        if sample:cmd+=['-ar',str(sample)]
        if channels:cmd+=['-ac',str(channels)]
        if fmt in {'mp4','mov','m4a'}:cmd+=['-movflags','+faststart']
        cmd+=['-progress','pipe:1','-nostats',str(target)]
        stats={'encoder':enc,'hardware':device,'hardwareFallback':reason,'fps':0,'speed':''}
        emit(stats=stats)
        with tempfile.TemporaryFile() as error:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=error,creationflags=FLAGS)
            for raw in proc.stdout:
                key,_,value=raw.decode('utf-8','replace').strip().partition('=')
                if key=='fps':stats['fps']=float(value or 0)
                elif key=='speed':stats['speed']=value
                elif key=='progress':emit(stats=dict(stats))
                elif key=='out_time_us' and duration:
                    try:emit(min(99,int(value)/1_000_000/max(.001,(end or duration)-start)*100),stats=dict(stats))
                    except ValueError:pass
            code=proc.wait();proc.stdout.close()
            if code:
                error.seek(0);raise RuntimeError(error.read().decode('utf-8','replace')[-3000:])
        return [target]
    try:return run(selected)
    except Exception as error:
        if selected=='cpu':raise
        target.unlink(missing_ok=True);reason=f'{selected} 編碼失敗，CPU 備援：{str(error)[-300:]}'
        return run('cpu')
