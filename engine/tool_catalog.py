"""Declarative toolbox capabilities. Every enabled item has an executable handler."""
def field(key,label,type='text',default='',**extra):return dict(key=key,label=label,type=type,default=default,**extra)
def select(key,label,values,default):return field(key,label,'select',default,choices=[{'value':v,'label':l} for v,l in values])
def number(key,label,default,min=0,max=100000):return field(key,label,'number',default,min=min,max=max)
REGION=field('region','處理區域','region',[.1,.1,.5,.5])
FORMAT=select('format','輸出格式',[('png','PNG'),('jpg','JPG'),('webp','WebP')],'png')
QUALITY=number('quality','圖片品質',90,1,100)
def tool(id,category,name,detail,sources,output,fields=(),engine=None,min=1,max=None,preview=False):
    if not engine and id.startswith(('video.','audio.')):engine='ffmpeg'
    return dict(id=id,category=category,name=name,detail=detail,sources=sources,output=output,fields=list(fields),engine=engine,minSources=min,maxSources=max,preview=preview)
CATALOG=[
 tool('pdf.reorder','PDF','PDF 頁面排序','輸入明確頁碼順序，例如 3,1,2；也可重複或擷取頁面',['pdf'],'pdf',[field('pages','頁碼順序',default='1')]),
 tool('pdf.crop','PDF','PDF 裁切','在頁面預覽拖曳區域，套用至所有頁面；原檔保持不變',['pdf'],'pdf',[REGION],preview=True),
 tool('pdf.compress','PDF','PDF 壓縮','無損重整或有損影像壓縮；不保證檔案一定變小',['pdf'],'pdf',[select('preset','壓縮方式',[('lossless','無損重整'),('screen','螢幕 · 有損'),('ebook','電子閱讀 · 有損'),('printer','列印')],'lossless')]),
 tool('pdf.watermark','PDF','PDF 添加浮水印','新增獨立標記物件，可由移除工具還原',['pdf'],'pdf',[field('text','浮水印文字',default='Watermark'),number('opacity','不透明度',.25,0,1),number('fontSize','字型大小',24,6,160),REGION],preview=True),
 tool('pdf.remove-watermark','PDF','PDF 移除獨立浮水印','只移除本程式標記、Artifact Watermark 或可獨立辨識的圖層；不刪除融合像素',['pdf'],'pdf'),
 tool('pdf.page-numbers','PDF','PDF 添加頁碼','在每頁頁尾添加數字',['pdf'],'pdf',[number('start','起始頁碼',1,1,100000)]),
 tool('pdf.protect','PDF','PDF 密碼保護','AES-256 加密；密碼不寫入歷史紀錄',['pdf'],'pdf',[field('password','密碼','password',secret=True)]),
 tool('pdf.decrypt','PDF','PDF 授權解密','僅使用已知且具修改權限的密碼，不繞過存取限制',['pdf'],'pdf',[field('password','授權密碼','password',secret=True),field('authorized','我有權修改此文件','switch',False)]),
 tool('pdf.ocr','PDF','PDF OCR／可搜尋 PDF','本機 Tesseract OCR；掃描辨識可能有誤，請校對',['pdf'],'pdf',[select('language','辨識語言',[('eng','English'),('chi_tra','繁體中文'),('eng+chi_tra','繁中＋English')],'eng+chi_tra'),field('onlyScans','略過已有文字的頁面','switch',True),number('dpi','OCR DPI',200,100,400)],engine='tessdata'),
 tool('image.resize','圖片','批次縮放','任一尺寸為 0 時維持比例',['image'],'image',[number('width','寬度 px · 0 自動',0),number('height','高度 px · 0 自動',0),FORMAT,QUALITY],preview=True),
 tool('image.crop','圖片','批次裁切','預覽拖曳區域，依比例套用到每張圖片',['image'],'image',[REGION,FORMAT,QUALITY],preview=True),
 tool('image.rotate','圖片','批次旋轉','另存處理後圖片，不修改原檔',['image'],'image',[select('angle','順時針角度',[('90','90°'),('180','180°'),('270','270°')],'90'),FORMAT,QUALITY],preview=True),
 tool('image.compress','圖片','圖片壓縮／目標大小','以合理最低品質搜尋目標；無法達成時明確回報。PNG 使用無損最佳化',['image'],'image',[FORMAT,QUALITY,number('targetMB','目標 MB · 0 不限',5,0,100000),number('minQuality','最低品質',40,1,100)],preview=True),
 tool('image.watermark','圖片','圖片添加浮水印','在手動選取區域加入文字',['image'],'image',[field('text','文字',default='Watermark'),number('opacity','不透明度',.5,0,1),number('fontSize','字型大小 px',28,6,300),field('color','文字顏色','color','#ffffff'),REGION,FORMAT,QUALITY],preview=True),
 tool('image.strip-metadata','圖片','清除 EXIF／GPS','重新輸出並清除 EXIF、GPS 與其他中繼資料',['image'],'image',[FORMAT,QUALITY],preview=True),
 tool('image.metadata','圖片','檢視中繼資料','讀取尺寸、EXIF／GPS、格式與動畫資訊，另存 JSON 報告',['image'],'json'),
 tool('image.repair','去浮水印／物件修復','圖片局部修補','OpenCV 非 AI 修補；無法完美恢復被遮住的原始像素',['image'],'image',[REGION,number('radius','修補半徑 px',3,1,20),FORMAT,QUALITY],engine='opencv',preview=True),
 tool('office.remove-watermark','去浮水印／物件修復','DOCX／PPTX 移除獨立浮水印','僅移除明確標示的浮水印 Shape；不刪除一般內文',['office'],'source',[field('watermarkName','物件名稱或完整文字',default='Watermark')]),
 tool('video.trim','影片','影片裁切','精準模式重新編碼；快速模式只做關鍵影格裁切',['video'],'media',[number('start','起點秒',0,0,1e9),number('end','終點秒 · 0 至結尾',0,0,1e9),field('copy','快速關鍵影格裁切','switch',False),select('format','輸出格式',[('mp4','MP4'),('mkv','MKV'),('mov','MOV')],'mp4')]),
 tool('video.merge','影片','影片合併','相容串流直接合併；不相容時統一尺寸及編碼，缺音軌片段補靜音',['video'],'media',[select('format','輸出格式',[('mp4','MP4'),('mkv','MKV')],'mp4')],min=2),
 tool('video.remux','影片','影片 Remux','直接重新封裝，不重新編碼；來源串流必須與容器相容',['video'],'media',[select('format','目標容器',[('mp4','MP4'),('mkv','MKV'),('mov','MOV'),('webm','WebM')],'mkv')]),
 tool('video.gif','影片','影片轉 GIF','輸出調色盤最佳化動畫 GIF',['video'],'gif',[number('start','起點秒',0,0,1e9),number('duration','長度秒',5,.1,1e6),number('fps','FPS',10,1,60),number('width','寬度 px',480,32,3840)]),
 tool('video.frame','影片','擷取指定影格','依時間另存 PNG',['video'],'png',[number('time','時間秒',0,0,1e9)],preview=True),
 tool('video.subtitles','影片','字幕抽取','僅支援文字字幕；序號依影片預覽的字幕列表',['video'],'subtitle',[number('stream','字幕序號 · 從 0 起',0,0,100),select('format','字幕格式',[('srt','SRT'),('ass','ASS'),('vtt','WebVTT')],'srt')]),
 tool('video.mux-subtitles','影片','字幕封裝','先加入影片，再加入 SRT／ASS／VTT；不燒入畫面',['video','subtitle'],'media',[select('format','輸出容器',[('mkv','MKV'),('mp4','MP4')],'mkv')],min=2,max=2),
 tool('video.delogo','去浮水印／物件修復','影片固定區域修補','FFmpeg delogo，非 AI；區域需保留邊界，不能完美恢復原始像素',['video'],'mp4',[REGION]),
 tool('audio.trim','音訊','音訊裁切','依時間精準另存音訊',['audio'],'media',[number('start','起點秒',0,0,1e9),number('end','終點秒 · 0 至結尾',0,0,1e9),select('format','輸出格式',[('mp3','MP3'),('wav','WAV'),('flac','FLAC')],'mp3')]),
 tool('audio.normalize','音訊','音量標準化','EBU R128 兩階段量測及處理',['audio','video'],'media',[number('lufs','整合音量 LUFS',-16,-70,-5),number('peak','True Peak dB',-1.5,-9,0),select('format','輸出格式',[('mp3','MP3'),('wav','WAV'),('flac','FLAC')],'wav')]),
 tool('archive.pack','壓縮','建立壓縮檔','ZIP／7Z／TAR；GZ 只接受單檔。支援加入資料夾',['any'],'archive',[select('format','壓縮格式',[('zip','ZIP'),('7z','7Z'),('tar','TAR'),('gz','GZ · 單檔')],'zip')],engine='sevenzip'),
 tool('archive.extract','壓縮','安全解壓縮','ZIP／7Z／RAR／TAR／GZ；檢查路徑、連結與展開資源，另存資料夾',['archive'],'folder',engine='sevenzip',max=1),
 tool('archive.convert','壓縮','壓縮格式轉換','先安全解壓，再建立 ZIP／7Z／TAR；不建立 RAR',['archive'],'archive',[select('format','輸出格式',[('zip','ZIP'),('7z','7Z'),('tar','TAR')],'zip')],engine='sevenzip',max=1),
 tool('archive.list','壓縮','壓縮檔內容預覽','不解壓，另存檔名、大小與路徑檢查 JSON',['archive'],'json',engine='sevenzip',max=1),
 tool('files.rename','檔案','另存批次重新命名','複製至輸出資料夾；保留原檔。可用 {stem}、{index}、{ext}',['any'],'source',[field('template','命名樣板',default='{stem}-{index}{ext}')]),
 tool('files.hash','檔案','SHA-256 驗證','逐位元讀取檔案，可輸入一個預期雜湊比對',['any'],'json',[field('expected','預期 SHA-256 · 可留空')]),
 tool('files.duplicates','檔案','重複檔案偵測','依大小與 SHA-256 分組，不刪除任何檔案',['any'],'json',min=2),
]

def catalog(engines):
    return [{**t,'available':not t['engine'] or bool(engines.get(t['engine'])),
        'reason':'' if not t['engine'] or engines.get(t['engine']) else '隨附 Runtime 不完整：'+t['engine']} for t in CATALOG]

def validate_tool(id,params,sources,engines):
    from pathlib import Path
    from detection import detect
    from registry import category
    definition=next((t for t in catalog(engines) if t['id']==id),None)
    if not definition:raise ValueError('不允許的工具')
    if not definition['available']:raise ValueError(definition['reason'])
    if len(sources)<definition['minSources'] or definition['maxSources'] and len(sources)>definition['maxSources']:raise ValueError('來源檔案數量不符合工具要求')
    clean=validate_params(definition,params)
    formats=[]
    for raw in sources:
        path=Path(raw)
        if not path.is_file() and not (id=='archive.pack' and path.is_dir()):raise ValueError('來源不存在或不是檔案')
        if 'any' not in definition['sources']:
            fmt=detect(path,engines)['format'];formats.append(fmt)
            if category(fmt) not in definition['sources']:raise ValueError('來源格式不符合此工具：'+path.name)
    if id=='video.mux-subtitles' and (category(formats[0])!='video' or category(formats[1])!='subtitle'):raise ValueError('請依序加入影片及文字字幕')
    if id=='office.remove-watermark' and any(f not in {'docx','pptx'} for f in formats):raise ValueError('只支援 DOCX／PPTX')
    return definition,clean

def validate_params(definition,params):
    clean={}
    for f in definition['fields']:
        value=params.get(f['key'],f['default'])
        if f['type']=='number':
            value=float(value)
            if not f['min']<=value<=f['max']:raise ValueError(f['label']+' 超出範圍')
        elif f['type']=='select':
            if value not in [c['value'] for c in f['choices']]:raise ValueError('無效選項：'+f['label'])
        elif f['type']=='region':
            if not isinstance(value,list) or len(value)!=4:raise ValueError('請選取處理區域')
            value=list(map(float,value));x,y,w,h=value
            if not (0<=x<1 and 0<=y<1 and 0<w<=1-x+1e-6 and 0<h<=1-y+1e-6):raise ValueError('無效處理區域')
        elif f['type']=='switch':value=bool(value)
        else:
            value=str(value)
            if len(value)>10000:raise ValueError('參數過長')
        clean[f['key']]=value
    return clean
