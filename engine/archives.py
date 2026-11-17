"""Bounded, traversal-resistant archive operations using bundled 7-Zip."""
from pathlib import Path,PurePosixPath
import json
import os
import shutil
import stat
import tarfile
import zipfile
import psutil
from runtime import command

def safe_name(name):
    normalized=name.replace('\\','/')
    path=PurePosixPath(normalized)
    if path.is_absolute() or not path.parts:raise ValueError('壓縮檔包含絕對路徑')
    reserved={'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
    for part in path.parts:
        if part in {'.','..'} or ':' in part or part.endswith((' ','.')) or any(ord(c)<32 for c in part) or part.split('.')[0].upper() in reserved:
            raise ValueError('壓縮檔包含不安全的路徑：'+name)
    return path

def entries(source,engines):
    source=Path(source)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            return [{'name':i.filename,'size':i.file_size,'packed':i.compress_size,'directory':i.is_dir(),
                     'link':stat.S_ISLNK(i.external_attr>>16)} for i in archive.infolist()]
    raw=command([engines['sevenzip'],'l','-slt','-ba','-sccUTF-8','--',source],timeout=60).decode('utf-8','replace')
    result=[]
    for block in raw.replace('\r\n','\n').split('\n\n'):
        values=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in values:continue
        result.append({'name':values['Path'],'size':int(values.get('Size','0') or 0),'packed':int(values.get('Packed Size','0') or 0),
            'directory':values.get('Folder')=='+' or 'D' in values.get('Attributes',''),
            'link':bool(values.get('Symbolic Link') or values.get('Hard Link') or values.get('Reparse Point'))})
    return result

def validate_entries(items,destination):
    total=0;seen=set();available=shutil.disk_usage(destination).free
    # Metadata and expanded data budgets follow actual RAM/disk availability.
    if len(items)*1024>psutil.virtual_memory().available//4:raise ValueError('壓縮檔項目過多，超出目前可用記憶體')
    for item in items:
        safe_name(item['name']);key=item['name'].replace('\\','/').rstrip('/').casefold()
        if key in seen:raise ValueError('壓縮檔包含重複或大小寫衝突路徑')
        seen.add(key)
        if item['link']:raise ValueError('不解壓含符號連結、硬連結或 Reparse Point 的壓縮檔')
        if item['size']<0:raise ValueError('無效展開大小')
        total+=item['size']
        if total>available*.8:raise ValueError('壓縮檔展開量超過可用磁碟空間的安全預算')
        if item['packed'] and item['size']/item['packed']>1000 and item['size']>psutil.virtual_memory().available//4:
            raise ValueError('疑似壓縮炸彈：異常壓縮比與展開大小')
    return total

def extract(source,target,engines):
    target=Path(target).resolve();target.mkdir(parents=True,exist_ok=True)
    items=entries(source,engines);validate_entries(items,target)
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for item in items:
                dest=target.joinpath(*safe_name(item['name']).parts)
                if not dest.resolve().is_relative_to(target):raise ValueError('不安全的解壓路徑')
                if item['directory']:dest.mkdir(parents=True,exist_ok=True);continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item['name']) as inp,dest.open('xb') as out:shutil.copyfileobj(inp,out,1024*1024)
    else:
        command([engines['sevenzip'],'x','-y','-o'+str(target),'--',source])
    total=0
    for file in target.rglob('*'):
        if file.is_symlink() or file.is_junction() or not file.resolve().is_relative_to(target):raise ValueError('解壓引擎產生不安全連結')
        if file.is_file():total+=file.stat().st_size
    if total>shutil.disk_usage(target).free+total:raise ValueError('展開空間不足')
    return target

def pack(sources,target,fmt,engines):
    if not sources:raise ValueError('沒有可重新封裝的項目')
    files=[];names=set()
    for raw in sources:
        source=Path(raw)
        if source.is_symlink() or source.is_junction():raise ValueError('不封裝符號連結或 Junction')
        if source.is_dir() and Path(target).resolve().is_relative_to(source.resolve()):raise ValueError('壓縮輸出不可位於來源資料夾內')
        key=source.name.casefold()
        if key in names:raise ValueError('來源檔名重複，請先重新命名')
        names.add(key)
        for file in source.rglob('*') if source.is_dir() else [source]:
            if file.is_symlink() or file.is_junction():raise ValueError('來源資料夾含連結，請移除後再封裝')
            if file.is_file() and Path(target).resolve().is_relative_to(file.resolve()):raise ValueError('不能封裝輸出本身')
        files.append(source)
    if fmt=='gz' and (len(files)!=1 or not files[0].is_file()):raise ValueError('GZ 只能封裝單一檔案，資料夾請先使用 TAR')
    command([engines['sevenzip'],'a','-t'+('gzip' if fmt=='gz' else fmt),'-y',target,'--',*files])
    if not Path(target).is_file():raise RuntimeError('壓縮引擎未產生檔案')
    return Path(target)

def execute(job,sources,stage,engines):
    op=job['operation'];params=job['params'];source=sources[0]
    if op=='archive.list':
        items=entries(source,engines);validate_entries(items,stage)
        target=stage/(source.stem+'-archive.json');target.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8');return [target]
    if op=='archive.extract':return [extract(source,stage/source.stem,engines)]
    fmt=params.get('format','zip');target=stage/(source.stem+'.'+fmt)
    if op=='archive.convert':
        folder=extract(source,stage/'.unpacked',engines)
        return [pack(list(folder.iterdir()),target,fmt,engines)]
    return [pack(sources,target,fmt,engines)]
