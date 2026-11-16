"""One isolated conversion per process. stdout is JSONL; never execute shell strings."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from formats import category, outputs

CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

def emit(progress=None, **data):
    if progress is not None: data['progress'] = min(100, max(0, progress))
    print(json.dumps(data, ensure_ascii=True), flush=True)

def number(options, key, default, low, high):
    value = float(options.get(key, default))
    if not low <= value <= high: raise ValueError(f'{key}: expected {low}–{high}')
    return value

def probe(path, ffprobe):
    result = subprocess.run([ffprobe, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)],
                            capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=30)
    if result.returncode: raise ValueError(result.stderr.decode('utf-8', 'replace')[-2000:])
    return json.loads(result.stdout)

def _legacy_media(job, sources, stage, engines):
    ffmpeg, ffprobe = engines.get('ffmpeg'), engines.get('ffprobe')
    if not ffmpeg or not ffprobe: raise RuntimeError('FFmpeg / ffprobe 未安裝。請查看設定 → 引擎狀態。')
    source = sources[0]; ext = job['format']; opt = job['options']
    info = probe(source, ffprobe)
    duration = float(info.get('format', {}).get('duration', 0) or 0)
    audio = ext in {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'opus'}
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-n', '-i', str(source)]
    if audio:
        cmd += ['-vn', '-map', '0:a:0']
        codec = {'mp3': 'libmp3lame', 'wav': 'pcm_s16le', 'flac': 'flac', 'aac': 'aac', 'm4a': 'aac', 'ogg': 'libvorbis', 'opus': 'libopus'}[ext]
        cmd += ['-c:a', codec]
        if ext not in {'wav', 'flac'}: cmd += ['-b:a', f"{int(number(opt,'audioBitrate',192,32,320))}k"]
    else:
        codec = opt.get('videoCodec', 'h264')
        if codec not in {'h264', 'h265', 'vp9', 'nvenc'}: raise ValueError('Unknown encoder')
        if ext == 'webm': codec = 'vp9'
        if ext == 'avi': codec = 'mpeg4'
        enc = {'h264': 'libx264', 'h265': 'libx265', 'vp9': 'libvpx-vp9', 'nvenc': 'h264_nvenc', 'mpeg4': 'mpeg4'}[codec]
        # Selecting NVENC requires an actual encode preflight, not just an encoder-list entry.
        if codec == 'nvenc':
            check = subprocess.run([ffmpeg, '-hide_banner', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=64x64:d=0.1', '-c:v', enc, '-f', 'null', '-'], capture_output=True, creationflags=CREATE_NO_WINDOW)
            if check.returncode: raise RuntimeError('NVIDIA NVENC 無法使用；請改用 CPU H.264。')
        cmd += ['-map', '0:v:0', '-map', '0:a:0?', '-c:v', enc]
        bitrate = int(number(opt, 'videoBitrate', 0, 0, 200000))
        if bitrate: cmd += ['-b:v', f'{bitrate}k']
        elif codec == 'nvenc': cmd += ['-cq', str(int(number(opt, 'crf', 23, 0, 51)))]
        elif codec == 'mpeg4': cmd += ['-q:v', '4']
        else: cmd += ['-crf', str(int(number(opt, 'crf', 23, 0, 51)))]
        if codec == 'vp9' and not bitrate: cmd += ['-b:v', '0']
        height = int(number(opt, 'videoHeight', 0, 0, 8640))
        if height: cmd += ['-vf', f'scale=-2:{height}']
        fps = number(opt, 'fps', 0, 0, 240)
        if fps: cmd += ['-r', str(fps)]
        cmd += ['-pix_fmt', 'yuv420p', '-c:a', 'libopus' if ext == 'webm' else 'aac', '-b:a', f"{int(number(opt,'audioBitrate',192,32,320))}k"]
    sample = int(number(opt, 'sampleRate', 0, 0, 192000))
    channels = int(number(opt, 'channels', 0, 0, 2))
    if sample: cmd += ['-ar', str(sample)]
    if channels: cmd += ['-ac', str(channels)]
    if ext in {'mp4', 'mov', 'm4a'}: cmd += ['-movflags', '+faststart']
    target = stage / f'{source.stem}.{ext}'
    cmd += ['-progress', 'pipe:1', '-nostats', str(target)]
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errors, creationflags=CREATE_NO_WINDOW)
        for raw in proc.stdout:
            line = raw.decode('utf-8', 'replace').strip()
            if line.startswith('out_time_us=') and duration:
                try: emit(min(99, int(line.split('=')[1]) / 1_000_000 / duration * 100))
                except ValueError: pass
        code = proc.wait()
        if code:
            errors.seek(0); raise RuntimeError(errors.read().decode('utf-8', 'replace')[-4000:])
    return [target]

def media(job,sources,stage,engines):
    from media_engine import convert_media
    return convert_media(job,sources,stage,engines)

def convert(job, stage, engines):
    if job.get('kind')=='download':
        from downloads import execute
        return execute(job,stage,engines)
    if job.get('operation'):
        from tools_engine import execute
        return execute(job,stage,engines)
    from detection import detect, normalize
    from registry import category, validate
    from adapters import ADAPTERS
    sources = [Path(p) for p in job['sources']]
    if not sources or any(not p.is_file() for p in sources): raise ValueError('來源檔案不存在')
    detected = [detect(p, engines)['format'] for p in sources]
    if any(not fmt for fmt in detected):raise ValueError('無法辨識實際檔案內容，或檔案損壞')
    job = dict(job, format=normalize(job['format']), category=category(detected[0]), sourceFormats=detected)
    edge = validate(detected[0], job['format'], engines, job.get('options'), len(sources))
    if len(sources)>1 and not (job['format']=='pdf' and all(category(f) in {'image','pdf'} for f in detected)):
        raise ValueError('合併僅支援圖片或 PDF → PDF')
    return ADAPTERS[edge['engine']].execute(job, sources, stage, engines)

def convert_pdf(job, sources, stage, engines):
    from PIL import Image, ImageOps
    kind = job['category']; fmt = job['format']; opt = job.get('options', {})
    import pymupdf as fitz
    if kind == 'pdf' and fmt != 'pdf':
        result = []
        with fitz.open(sources[0]) as doc:
            for i in range(len(doc)):
                dpi = number(opt, 'pdfDpi', 144, 36, 600)
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72), alpha=False)
                target = stage / f'{sources[0].stem}-{i+1:03d}.{fmt}'
                pix.save(str(target)); result.append(target); emit((i+1)/len(doc)*99)
        return result
    doc = fitz.open()
    try:
        for i, source in enumerate(sources):
            if job['sourceFormats'][i] == 'pdf':
                with fitz.open(source) as part:
                    if part.needs_pass: raise ValueError('加密 PDF 需要先解密')
                    page_spec = str(opt.get('pages', '')).strip()
                    if page_spec and len(sources) == 1:
                        selected = []
                        for item in page_spec.split(','):
                            bounds = item.strip().split('-')
                            start = int(bounds[0]); end = int(bounds[-1])
                            if not 1 <= start <= end <= len(part): raise ValueError('PDF 頁碼超出範圍')
                            selected.extend(range(start-1,end))
                        for page in selected: doc.insert_pdf(part, from_page=page, to_page=page)
                    else: doc.insert_pdf(part)
            else:
                with Image.open(source) as image:
                    image = ImageOps.exif_transpose(image).convert('RGB')
                    import io
                    buf = io.BytesIO(); image.save(buf, format='PNG')
                    page = doc.new_page(width=image.width, height=image.height)
                    page.insert_image(page.rect, stream=buf.getvalue())
            emit((i+1)/len(sources)*90)
        rotate = int(number(opt, 'rotation', 0, 0, 270))
        if rotate not in {0,90,180,270}: raise ValueError('旋轉須為 0/90/180/270')
        for page in doc: page.set_rotation((page.rotation+rotate)%360)
        if opt.get('split'):
            result = []
            for i in range(len(doc)):
                target = stage / f'{sources[0].stem}-{i+1:03d}.pdf'
                with fitz.open() as part:
                    part.insert_pdf(doc, from_page=i, to_page=i); part.save(str(target))
                result.append(target)
            return result
        target = stage / f'{sources[0].stem}.pdf'; doc.save(str(target), garbage=3, deflate=True)
        return [target]
    finally: doc.close()

def convert_image(job, sources, stage, engines):
    from PIL import Image, ImageOps
    from runtime import image_plugins
    image_plugins()
    kind = job['category']; fmt = job['format']; opt = job.get('options', {})
    with Image.open(sources[0]) as source:
        image = ImageOps.exif_transpose(source)
        width = int(number(opt, 'width', 0, 0, 100000)); height = int(number(opt, 'height', 0, 0, 100000))
        if width or height:
            if not width: width = max(1,round(image.width*height/image.height))
            if not height: height = max(1,round(image.height*width/image.width))
            image = image.resize((width,height),Image.Resampling.LANCZOS)
        if fmt in {'jpg','bmp'}:
            background = str(opt.get('matte', '#ffffff'))
            base = Image.new('RGB', image.size, background)
            if 'A' in image.getbands(): base.paste(image, mask=image.getchannel('A'))
            else: base.paste(image.convert('RGB'))
            image = base
        target = stage / f'{sources[0].stem}.{fmt}'
        image.save(target, format={'jpg':'JPEG','tiff':'TIFF','heic':'HEIF'}.get(fmt,fmt.upper()), quality=int(number(opt,'quality',90,1,100)))
        return [target]

def convert_office(job, sources, stage, engines):
    from PIL import Image, ImageOps
    kind = job['category']; fmt = job['format']; opt = job.get('options', {})
    soffice = engines.get('soffice')
    if not soffice: raise RuntimeError('Office 轉檔需要本機 LibreOffice。安裝後重新整理引擎狀態。')
    with tempfile.TemporaryDirectory(prefix='rai-lo-') as profile:
        result = subprocess.run([soffice, '-env:UserInstallation='+Path(profile).as_uri(), '--headless', '--convert-to', fmt, '--outdir', str(stage), str(sources[0])], capture_output=True, creationflags=CREATE_NO_WINDOW, timeout=600)
        files = list(stage.glob('*.'+fmt))
        if result.returncode or not files: raise RuntimeError((result.stdout+result.stderr).decode('utf-8','replace')[-3000:] or 'LibreOffice 未產生輸出')
        return files


def run_worker(spec):
    job, engines, stage = spec['job'], dict(spec['engines'],hardwareCapabilities=spec.get('hardwareCapabilities')), Path(spec['stage'])
    try:
        files = convert(job, stage, engines)
        emit(100, files=[str(p) for p in files])
        return 0
    except Exception as error:
        emit(error=str(error)); return 1
