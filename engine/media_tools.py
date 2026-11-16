"""Video/audio editing with stream-copy paths where they preserve the requested operation."""
import json
from pathlib import Path
import re
from runtime import command

def execute(job,sources,stage,engines):
    from worker import probe,emit
    from media_engine import convert_media
    ffmpeg=engines['ffmpeg'];p=job['params'];op=job['operation'];source=sources[0]
    fmt=p.get('format','gif' if op=='video.gif' else 'png' if op=='video.frame' else 'mp4')
    target=stage/(source.stem+'-processed.'+fmt)
    info=probe(source,engines['ffprobe']);duration=float(info.get('format',{}).get('duration',0) or 0)
    if op in {'video.trim','audio.trim','video.delogo'}:
        if op=='video.trim' and p.get('copy'):
            start=float(p['start']);end=float(p['end'])
            if start<0 or start>=duration or end and not start<end<=duration:raise ValueError('裁切時間超出範圍')
            args=[ffmpeg,'-v','error','-nostdin','-ss',str(start),'-i',source]
            if end:args+=['-t',str(end-start)]
            command([*args,'-map','0','-c','copy','-n',target]);emit(stats={'encoder':'stream copy','warning':'快速裁切依關鍵影格，時間可能有差異'});return [target]
        options={**job.get('options',{})}
        if op!='video.delogo':options.update(trimStart=p.get('start',0),trimEnd=p.get('end',0))
        return convert_media(dict(job,format=fmt,options=options),sources,stage,engines)
    if op=='video.remux':
        command([ffmpeg,'-v','error','-nostdin','-i',source,'-map','0','-c','copy','-n',target]);emit(stats={'encoder':'stream copy'});return [target]
    if op=='video.frame':
        if float(p['time'])>=duration and duration:raise ValueError('影格時間超出範圍')
        command([ffmpeg,'-v','error','-nostdin','-ss',str(p['time']),'-i',source,'-frames:v','1','-n',target]);return [target]
    if op=='video.gif':
        if float(p['start'])>=duration:raise ValueError('起點超出影片範圍')
        graph=f"fps={int(p['fps'])},scale={int(p['width'])}:-1:flags=lanczos,split[a][b];[a]palettegen[pal];[b][pal]paletteuse"
        command([ffmpeg,'-v','error','-nostdin','-ss',str(p['start']),'-t',str(p['duration']),'-i',source,'-filter_complex',graph,'-an','-n',target]);return [target]
    if op=='video.subtitles':
        subtitles=[s for s in info['streams'] if s.get('codec_type')=='subtitle']
        index=int(p['stream'])
        if index>=len(subtitles):raise ValueError('沒有指定序號的字幕軌')
        if subtitles[index]['codec_name'] not in {'subrip','ass','ssa','mov_text','webvtt','text'}:raise ValueError('此字幕是圖片，不能直接抽取為文字字幕')
        command([ffmpeg,'-v','error','-nostdin','-i',source,'-map',f'0:s:{index}','-n',target]);return [target]
    if op=='video.mux-subtitles':
        command([ffmpeg,'-v','error','-nostdin','-i',source,'-i',sources[1],'-map','0','-map','1:0','-c','copy','-c:s','mov_text' if fmt=='mp4' else 'copy','-n',target]);return [target]
    if op=='audio.normalize':
        base=f"loudnorm=I={p['lufs']}:TP={p['peak']}:LRA=11"
        analysis=command([ffmpeg,'-hide_banner','-nostdin','-i',source,'-vn','-af',base+':print_format=json','-f','null','-'],return_stderr=True).decode('utf-8','replace')
        blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',analysis,re.S)
        if not blocks:raise ValueError('音量量測失敗')
        data=json.loads(blocks[-1]);filters=base
        if data.get('input_i') not in {'-inf','inf'}:
            filters+=':measured_I='+data['input_i']+':measured_TP='+data['input_tp']+':measured_LRA='+data['input_lra']+':measured_thresh='+data['input_thresh']+':offset='+data['target_offset']+':linear=true'
        command([ffmpeg,'-v','error','-nostdin','-i',source,'-vn','-af',filters,'-ar','48000','-n',target]);emit(stats={'loudnessInput':data,'targetLUFS':p['lufs']});return [target]
    if op=='video.merge':return merge(job,sources,stage,engines,target)
    raise ValueError('Unsupported media tool')

def merge(job,sources,stage,engines,target):
    from worker import probe,emit
    info=[probe(p,engines['ffprobe']) for p in sources]
    def signature(data):return [(s.get('codec_type'),s.get('codec_name'),s.get('width'),s.get('height'),s.get('sample_rate'),s.get('channels'),s.get('r_frame_rate'),s.get('time_base')) for s in data['streams']]
    if all(signature(d)==signature(info[0]) for d in info):
        listing=stage/'concat.txt'
        listing.write_text('\n'.join("file '"+str(p.resolve()).replace('\\','/').replace("'","'\\''")+"'" for p in sources),encoding='utf-8')
        try:
            command([engines['ffmpeg'],'-v','error','-nostdin','-f','concat','-safe','0','-i',listing,'-map','0','-c','copy','-n',target]);emit(stats={'encoder':'stream copy'});return [target]
        except RuntimeError:target.unlink(missing_ok=True)
    first=next(s for s in info[0]['streams'] if s.get('codec_type')=='video');width=int(first['width'])//2*2;height=int(first['height'])//2*2
    arguments=[engines['ffmpeg'],'-v','error','-nostdin'];filters=[];pads=[]
    for i,(source,data) in enumerate(zip(sources,info)):
        arguments+=['-i',source]
        filters.append(f'[{i}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,setpts=PTS-STARTPTS[v{i}]')
        if any(s.get('codec_type')=='audio' for s in data['streams']):filters.append(f'[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]')
        else:filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={float(data['format']['duration'])},asetpts=PTS-STARTPTS[a{i}]")
        pads.append(f'[v{i}][a{i}]')
    filters.append(''.join(pads)+f'concat=n={len(sources)}:v=1:a=1[v][a]')
    command([*arguments,'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-c:v','libx264','-preset','medium','-crf','23','-c:a','aac','-pix_fmt','yuv420p','-n',target])
    emit(stats={'encoder':'libx264','warning':'來源串流不相容，已統一尺寸、FPS 與音訊後合併'});return [target]
