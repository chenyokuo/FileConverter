"""Read-only metadata/hash tools and copy-based batch naming."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

def image_metadata(path):
    from PIL import Image,ExifTags
    from runtime import image_plugins
    image_plugins()
    with Image.open(path) as image:
        metadata={ExifTags.TAGS.get(k,str(k)):str(v) for k,v in image.getexif().items()}
        return {'name':path.name,'size':path.stat().st_size,'format':image.format,'dimensions':list(image.size),'frames':getattr(image,'n_frames',1),'exif':metadata}

def office_remove(source,target,name):
    from lxml import etree
    from archives import entries,validate_entries
    validate_entries(entries(source,{}),target.parent)
    removed=0
    parser=etree.XMLParser(resolve_entities=False,no_network=True)
    with zipfile.ZipFile(source) as inp,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
        for entry in inp.infolist():
            data=inp.read(entry)
            if entry.filename.endswith('.xml') and entry.filename.startswith(('word/','ppt/')):
                root=etree.fromstring(data,parser)
                for node in list(root.iter()):
                    if not isinstance(node.tag,str) or node is not root and not any(a is root for a in node.iterancestors()):continue
                    tag=etree.QName(node).localname
                    if tag not in {'shape','sp','pic','drawing'}:continue
                    identifiers=[str(v) for child in node.iter() for k,v in child.attrib.items() if etree.QName(k).localname in {'id','name','title','descr'}]
                    text=''.join(node.itertext()).strip()
                    known=any('powerpluswatermarkobject' in x.lower() or 'watermark' in x.lower() or '浮水印' in x for x in identifiers)
                    requested=bool(name.strip()) and (name in identifiers or text==name)
                    if (known or requested) and node.getparent() is not None:
                        node.getparent().remove(node);removed+=1
                data=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            out.writestr(entry,data)
    if not removed:target.unlink(missing_ok=True);raise ValueError('找不到獨立標記的浮水印 Shape；未刪除一般內文')
    return removed

def execute(job,sources,stage,engines):
    from worker import emit
    op=job['operation'];params=job['params']
    if op=='image.metadata':data=[image_metadata(p) for p in sources]
    elif op=='office.remove-watermark':
        result=[];removed=0
        for i,p in enumerate(sources):
            target=stage/(p.stem+'-clean'+p.suffix);removed+=office_remove(p,target,params['watermarkName']);result.append(target);emit((i+1)/len(sources)*95)
        emit(stats={'removedWatermarks':removed});return result
    elif op=='files.rename':
        from archives import safe_name
        result=[]
        for i,p in enumerate(sources):
            try:name=params['template'].format(stem=p.stem,index=i+1,ext=p.suffix)
            except (KeyError,ValueError):raise ValueError('命名樣板只支援 {stem}、{index}、{ext}')
            if len(safe_name(name).parts)!=1:raise ValueError('檔名不可包含資料夾')
            target=stage/name;index=1
            while target.exists():target=stage/f'{Path(name).stem} ({index}){Path(name).suffix}';index+=1
            shutil.copy2(p,target);result.append(target);emit((i+1)/len(sources)*95)
        return result
    else:
        records=[];total=sum(p.stat().st_size for p in sources);done=0
        for p in sources:
            before=p.stat();digest=hashlib.sha256()
            with p.open('rb') as inp:
                while block:=inp.read(4*1024*1024):digest.update(block);done+=len(block);emit(done/max(1,total)*95)
            after=p.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('來源檔案在計算時被修改')
            records.append({'path':str(p),'size':before.st_size,'sha256':digest.hexdigest()})
        if op=='files.duplicates':
            groups={}
            for item in records:groups.setdefault((item['size'],item['sha256']),[]).append(item['path'])
            data={'groups':[{'size':k[0],'sha256':k[1],'files':v} for k,v in groups.items() if len(v)>1],'scanned':len(records)}
        else:
            expected=params.get('expected','').lower().strip()
            if expected and not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('預期 SHA-256 格式錯誤')
            for item in records:item['matches']=item['sha256']==expected if expected else None
            if expected and not all(item['matches'] for item in records):emit(stats={'warning':'SHA-256 與預期不符','hashMatched':False})
            data={'files':records,'expected':expected}
    target=stage/(sources[0].stem+'-report.json');target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');return [target]
