"""PDF operations always write to a distinct staging file."""
from pathlib import Path
import io
import re
from runtime import command

def pages(spec,count):
    result=[]
    for token in str(spec).split(','):
        bounds=token.strip().split('-')
        if len(bounds)>2 or not all(x.isdigit() for x in bounds):raise ValueError('無效頁碼')
        first,last=int(bounds[0]),int(bounds[-1])
        if not 1<=first<=last<=count:raise ValueError('頁碼超出範圍')
        result.extend(range(first-1,last))
    return result

def region(rect,value):
    import pymupdf
    x,y,w,h=map(float,value)
    return pymupdf.Rect(rect.x0+x*rect.width,rect.y0+y*rect.height,rect.x0+(x+w)*rect.width,rect.y0+(y+h)*rect.height)

def remove_independent_watermarks(source,target):
    import pymupdf
    removed=0
    with pymupdf.open(source) as doc:
        for page in doc:
            for xref in page.get_contents():
                data=doc.xref_stream(xref)
                if data.startswith(b'% FileConverter-Watermark\n'):
                    doc.update_stream(xref,b'');removed+=1
        if removed:doc.save(target,garbage=4,deflate=True);return removed
    # Also recognize standards-based independently marked Artifact/Watermark blocks.
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import ContentStream
    reader=PdfReader(source);writer=PdfWriter()
    for page in reader.pages:
        content=page.get_contents()
        if content:
            stream=ContentStream(content,reader);operations=[];drop=0
            for operands,operator in stream.operations:
                if drop:
                    if operator in {b'BDC',b'BMC'}:drop+=1
                    elif operator==b'EMC':drop-=1
                    continue
                if operator==b'BDC' and len(operands)>1:
                    tag,properties=operands[:2]
                    if str(tag)=='/OC' and not isinstance(properties,dict):
                        properties=page.get('/Resources',{}).get('/Properties',{}).get(properties,properties)
                    if hasattr(properties,'get_object'):properties=properties.get_object()
                    artifact=str(tag)=='/Artifact' and isinstance(properties,dict) and str(properties.get('/Subtype'))=='/Watermark'
                    layer=str(tag)=='/OC' and isinstance(properties,dict) and ('watermark' in str(properties.get('/Name','')).lower() or '浮水印' in str(properties.get('/Name','')))
                    if artifact or layer:
                        drop=1;removed+=1;continue
                operations.append((operands,operator))
            if drop:raise ValueError('浮水印標記不完整，未修改文件')
            stream.operations=operations;page.replace_contents(stream)
        writer.add_page(page)
    if not removed:raise ValueError('找不到可獨立辨識的浮水印物件；未刪除任何一般頁面內容')
    with target.open('wb') as out:writer.write(out)
    return removed

def execute(job,sources,stage,engines):
    import pymupdf
    from worker import emit
    source=sources[0];op=job['operation'];params=job['params'];target=stage/(source.stem+'-processed.pdf')
    if op=='pdf.remove-watermark':
        count=remove_independent_watermarks(source,target);emit(stats={'removedWatermarks':count});return [target]
    if op=='pdf.compress' and params['preset']!='lossless':
        if not engines.get('ghostscript'):raise RuntimeError('缺少 Ghostscript Runtime')
        command([engines['ghostscript'],'-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite','-dPDFSETTINGS=/'+params['preset'],'-sOutputFile='+str(target),source])
        emit(stats={'inputBytes':source.stat().st_size,'outputBytes':target.stat().st_size});return [target]
    with pymupdf.open(source) as doc:
        if job.get('previewOnly') and len(doc)>1:doc.select([0])
        if doc.needs_pass:
            auth=doc.authenticate(params.get('password',''))
            if not auth:raise ValueError('密碼不正確')
            if op=='pdf.decrypt' and not auth&4 and not doc.permissions&pymupdf.PDF_PERM_MODIFY:raise ValueError('此密碼沒有修改權限，請提供擁有者密碼')
        if op=='pdf.decrypt' and not params.get('authorized'):raise ValueError('請確認有權修改此文件')
        if op=='pdf.reorder':doc.select(pages(params['pages'],len(doc)))
        elif op=='pdf.crop':
            for page in doc:
                crop=region(page.rect,params['region'])*page.derotation_matrix
                page.set_cropbox(crop)
        elif op=='pdf.watermark':
            if not params['text'].strip():raise ValueError('請輸入浮水印文字')
            for page in doc:
                before=set(page.get_contents());box=region(page.rect,params['region'])
                amount=page.insert_textbox(box,params['text'],fontsize=params['fontSize'],fontname='china-t',align=1,color=(.5,.5,.5),fill_opacity=params['opacity'],overlay=True)
                if amount<0:raise ValueError('浮水印區域太小，請放大區域或縮小字型')
                for xref in set(page.get_contents())-before:
                    doc.update_stream(xref,b'% FileConverter-Watermark\n'+doc.xref_stream(xref))
        elif op=='pdf.page-numbers':
            for i,page in enumerate(doc):page.insert_text((page.rect.width/2,page.rect.height-24),str(i+int(params['start'])),fontsize=11)
        elif op=='pdf.ocr':
            result=pymupdf.open();languages=params['language'];tessdata=engines.get('tessdata')
            if not tessdata:raise RuntimeError('OCR 字庫不完整')
            for i,page in enumerate(doc):
                if params['onlyScans'] and page.get_text().strip():result.insert_pdf(doc,from_page=i,to_page=i)
                else:
                    pix=page.get_pixmap(dpi=int(params['dpi']),alpha=False)
                    data=pix.pdfocr_tobytes(compress=True,language=languages,tessdata=tessdata)
                    with pymupdf.open(stream=data,filetype='pdf') as recognized:result.insert_pdf(recognized)
                emit((i+1)/len(doc)*95)
            result.save(target,garbage=4,deflate=True);result.close();return [target]
        encryption=pymupdf.PDF_ENCRYPT_NONE;extra={}
        if op=='pdf.protect':
            password=params.get('password','')
            if not password:raise ValueError('密碼不可為空白')
            encryption=pymupdf.PDF_ENCRYPT_AES_256;extra={'owner_pw':password,'user_pw':password}
        doc.save(target,garbage=4,deflate=True,use_objstms=1,encryption=encryption,**extra)
    emit(stats={'inputBytes':source.stat().st_size,'outputBytes':target.stat().st_size})
    return [target]
