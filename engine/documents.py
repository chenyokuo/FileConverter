"""Document, spreadsheet, PDF and vector adapters with local runtimes only."""
from pathlib import Path
import tempfile
import os
import shutil
import time
import zipfile
from runtime import command

def convert_document(job,sources,stage,engines):
    fmt=job['format'];source=sources[0];source_fmt=job['sourceFormats'][0]
    if source_fmt=='pdf' and fmt=='txt':
        import pymupdf
        with pymupdf.open(source) as doc:text='\n\f\n'.join(page.get_text() for page in doc)
        target=stage/(source.stem+'.txt');target.write_text(text,encoding='utf-8');return [target]
    if source_fmt=='pdf' and fmt=='docx':
        from pdf2docx import Converter
        import contextlib,sys
        target=stage/(source.stem+'.docx')
        # Engine logs must never corrupt the worker JSONL protocol.
        with contextlib.redirect_stdout(sys.stderr):
            converter=Converter(str(source))
            try:converter.convert(str(target),multi_processing=False)
            finally:converter.close()
        if not target.is_file():raise RuntimeError('PDF → DOCX 未產生文件')
        return [target]
    if source_fmt in {'md','html','txt'} and fmt in {'md','html','docx','txt','pdf'} or source_fmt=='docx' and fmt in {'md','html'}:
        pandoc=engines.get('pandoc')
        if not pandoc:raise RuntimeError('缺少隨附 Pandoc Runtime')
        target=stage/(source.stem+('.docx' if fmt=='pdf' else '.'+fmt))
        reader={'md':'markdown','html':'html','txt':'markdown','docx':'docx'}[source_fmt]
        writer='plain' if fmt=='txt' else 'docx' if fmt=='pdf' else 'markdown' if fmt=='md' else fmt
        command([pandoc,'--sandbox','--from',reader,'--to',writer,'--standalone','--output',target,source])
        if fmt!='pdf':return [target]
        return office(job,[target],stage,engines)
    return office(job,sources,stage,engines)

def office(job,sources,stage,engines):
    soffice=engines.get('soffice')
    if not soffice:raise RuntimeError('隨附 LibreOffice Runtime 不完整，請修復 File Converter')
    fmt=job['format'];source=sources[0]
    filters={'doc':'MS Word 97','docx':'Office Open XML Text','odt':'writer8','rtf':'Rich Text Format',
             'xls':'MS Excel 97','xlsx':'Calc MS Excel 2007 XML','ods':'calc8','ppt':'MS PowerPoint 97',
             'pptx':'Impress MS PowerPoint 2007 XML','odp':'impress8','csv':'Text - txt - csv (StarCalc):44,34,76,1',
             'tsv':'Text - txt - csv (StarCalc):9,34,76,1','txt':'Text (encoded):UTF8'}
    with tempfile.TemporaryDirectory(prefix='office-profile-',dir=stage,ignore_cleanup_errors=True) as profile:
        user=Path(profile)/'user';user.mkdir()
        (user/'registrymodifications.xcu').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry">
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop></item>
</oor:items>''',encoding='utf-8')
        arguments=[soffice,'-env:UserInstallation='+Path(profile).as_uri(),'--headless','--nologo','--nodefault','--norestore']
        if source.suffix.lower() in {'.csv','.tsv'}:
            arguments+=['--infilter=Text - txt - csv (StarCalc):'+('9' if source.suffix.lower()=='.tsv' else '44')+',34,76,1']
        arguments+=['--convert-to',fmt+(':'+filters[fmt] if fmt in filters else ''),'--outdir',stage,source]
        command(arguments,env=dict(os.environ,SAL_DISABLE_OPENCL='1'))
        # Office can finish writing its private deployment cache just after exit.
        profile_path=Path(profile).resolve()
        if not profile_path.is_relative_to(Path(stage).resolve()):raise ValueError('Invalid Office profile path')
        from fsutils import remove_tree
        remove_tree(profile_path,stage)
    files=list(stage.glob('*.'+fmt))
    if not files:raise RuntimeError('LibreOffice 未產生輸出，請確認文件沒有損壞或被加密')
    return files

def convert_vector(job,sources,stage,engines):
    import pymupdf
    source=sources[0];src=job['sourceFormats'][0];fmt=job['format'];opt=job.get('options',{})
    pdf=source
    if src=='eps':
        gs=engines.get('ghostscript')
        if not gs:raise RuntimeError('缺少 Ghostscript Runtime')
        pdf=stage/(source.stem+'-intermediate.pdf')
        command([gs,'-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=pdfwrite','-dEPSCrop','-sOutputFile='+str(pdf),source])
    elif src=='svg':
        pdf=stage/(source.stem+'-intermediate.pdf')
        with pymupdf.open(source) as doc:data=doc.convert_to_pdf()
        pdf.write_bytes(data)
    if fmt=='pdf':
        target=stage/(source.stem+'.pdf')
        if target!=pdf:target.write_bytes(pdf.read_bytes())
        return [target]
    if fmt=='eps':
        gs=engines.get('ghostscript')
        if not gs:raise RuntimeError('缺少 Ghostscript Runtime')
        command([gs,'-dSAFER','-dBATCH','-dNOPAUSE','-sDEVICE=eps2write','-sOutputFile='+str(stage/(source.stem+'-%03d.eps')),pdf])
        return list(stage.glob('*.eps'))
    result=[]
    with pymupdf.open(pdf) as doc:
        for i,page in enumerate(doc):
            target=stage/f'{source.stem}-{i+1:03d}.{fmt}'
            if fmt=='svg':target.write_text(page.get_svg_image(),encoding='utf-8')
            else:page.get_pixmap(dpi=int(opt.get('pdfDpi',144))).save(target)
            result.append(target)
    return result

def convert_ebook(job,sources,stage,engines):
    runtime=engines.get('calibre')
    if not runtime:raise RuntimeError('缺少 Calibre Runtime')
    target=stage/(sources[0].stem+'.'+job['format'])
    env=dict(os.environ,CALIBRE_CONFIG_DIRECTORY=str(stage/'.calibre-config'),CALIBRE_CACHE_DIRECTORY=str(stage/'.calibre-cache'))
    command([runtime,sources[0],target],env=env)
    if not target.is_file():raise RuntimeError('電子書引擎未產生輸出')
    return [target]
