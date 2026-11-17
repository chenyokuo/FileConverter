"""Capture/restore only this application's optional HKCU verbs for native QA."""
from pathlib import Path
import base64,json,sys,winreg
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from context_menu import keys,OWNER,update
engines={k:True for k in ['ffmpeg','ffprobe','soffice','pandoc','calibre','ghostscript','pdf2docx','heif','sevenzip']}
allowed={name for name,_,_ in keys(engines)}
state_path=Path(sys.argv[2]).resolve();assert state_path.is_relative_to(ROOT/'.tools')
def values(name):
 try:
  with winreg.OpenKey(winreg.HKEY_CURRENT_USER,name) as key:
   result=[]
   for i in range(winreg.QueryInfoKey(key)[1]):
    field,value,kind=winreg.EnumValue(key,i)
    result.append({'field':field,'data':base64.b64encode(value).decode() if isinstance(value,bytes) else value,'kind':kind,'binary':isinstance(value,bytes)})
   return result
 except FileNotFoundError:return None
if sys.argv[1]=='capture':
 records={name:values(name) for name in allowed|{n+r'\command' for n in allowed}}
 state_path.write_text(json.dumps(records),encoding='utf-8');print('Captured only File Converter verb keys.')
elif sys.argv[1]=='restore':
 records=json.loads(state_path.read_text());assert set(records)==allowed|{n+r'\command' for n in allowed}
 candidate=Path(sys.argv[3]).resolve();assert candidate.name=='FileConverter.exe' and candidate.is_relative_to(ROOT)
 update(str(candidate),False,engines)
 for name,rows in records.items():
  if rows is not None:
   with winreg.CreateKey(winreg.HKEY_CURRENT_USER,name) as key:
    for row in rows:winreg.SetValueEx(key,row['field'],0,row['kind'],base64.b64decode(row['data']) if row['binary'] else row['data'])
 canon=lambda rows:None if rows is None else sorted(rows,key=lambda row:row['field'])
 assert all(canon(values(name))==canon(rows) for name,rows in records.items())
 print('Restored exact original application verbs; no default associations touched.')
elif sys.argv[1]=='verify':
 records=json.loads(state_path.read_text());assert set(records)==allowed|{n+r'\command' for n in allowed}
 canon=lambda rows:None if rows is None else sorted(rows,key=lambda row:row['field'])
 assert all(canon(values(name))==canon(rows) for name,rows in records.items())
 print('Verified exact original application verbs without registry writes.')
else:raise ValueError('Use capture, restore or verify')
