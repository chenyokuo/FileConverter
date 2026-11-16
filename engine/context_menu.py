"""Opt-in HKCU shell verbs only. Never write associations, OpenWith or DefaultIcon."""
import os
from pathlib import Path
from registry import registry
OWNER='studio.rai.converter'
BASE=r'Software\Classes'
VERB='FileConverter'

def keys(engines):
    result=[(BASE+r'\*\shell'+'\\'+VERB,'使用 File Converter 開啟','')]
    for edge in registry(engines)['edges']:
        if edge['available'] and edge['target'] in {'pdf','jpg','mp3'} and edge['source']!=edge['target']:
            result.append((BASE+r'\SystemFileAssociations\.'+edge['source']+r'\shell'+'\\'+VERB+'To'+edge['target'].upper(),'File Converter → '+edge['target'].upper(),edge['target']))
    return result

def executable(app_exe):
    if os.name!='nt' or not app_exe:raise ValueError('右鍵整合只可從 Windows 桌面應用程式啟用')
    path=Path(app_exe).resolve()
    if path.name!='FileConverter.exe' or not path.is_file():raise ValueError('應用程式執行檔無效')
    return path

def status(app_exe):
    try:path=executable(app_exe)
    except ValueError as error:return {'available':False,'enabled':False,'reason':str(error)}
    import winreg as reg
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER,BASE+r'\*\shell'+'\\'+VERB) as key:
            enabled=reg.QueryValueEx(key,'Owner')[0]==OWNER and reg.QueryValueEx(key,'Executable')[0]==str(path)
    except OSError:enabled=False
    return {'available':True,'enabled':enabled,'reason':''}

def update(app_exe,enabled,engines):
    path=executable(app_exe);import winreg as reg
    # Include all known format verbs when disabling, even if a runtime became unavailable.
    all_keys=keys({k:True for k in ['ffmpeg','ffprobe','soffice','pandoc','calibre','ghostscript','pdf2docx','heif','sevenzip']})
    for name,label,target in all_keys:
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER,name) as key:
                owned=reg.QueryValueEx(key,'Owner')[0]==OWNER
            if not owned:raise ValueError('同名右鍵項目不屬於此應用程式，已保留')
            try:reg.DeleteKey(reg.HKEY_CURRENT_USER,name+r'\command')
            except FileNotFoundError:pass
            reg.DeleteKey(reg.HKEY_CURRENT_USER,name)
        except FileNotFoundError:pass
    if enabled:
        for name,label,target in keys(engines):
            with reg.CreateKey(reg.HKEY_CURRENT_USER,name) as key:
                for field,value in [('',label),('Owner',OWNER),('Executable',str(path)),('Icon',str(path)+',0'),('MultiSelectModel','Single')]:reg.SetValueEx(key,field,0,reg.REG_SZ,value)
            command='"'+str(path)+'" --open "%1"'+(' --target '+target if target else '')
            with reg.CreateKey(reg.HKEY_CURRENT_USER,name+r'\command') as key:reg.SetValueEx(key,'',0,reg.REG_SZ,command)
    return status(app_exe)
