"""Validated, local, unary pipelines. No arbitrary shell, scripts or hidden routes."""
from pathlib import Path
import shutil
from registry import category,normalize,validate
from tool_catalog import catalog,validate_params

def workflow_tools(engines):
    return [t for t in catalog(engines) if t['available'] and t['minSources']==1 and
        t['output'] not in {'folder','json','subtitle','archive'} and not t['id'].startswith('archive.') and
        not any(f.get('secret') for f in t['fields'])]

def plan(config,engines):
    source=normalize(config.get('source',''));steps=config.get('steps',[])
    if category(source)=='unsupported':raise ValueError('請選擇實際來源格式')
    if not isinstance(steps,list) or not 1<=len(steps)<=30:raise ValueError('流程需有 1–30 個步驟')
    tools={t['id']:t for t in workflow_tools(engines)};clean=[];current=source
    for i,step in enumerate(steps):
        before=current
        if step.get('type')=='convert':
            target=normalize(step.get('target',''));options=step.get('options') or {}
            if not isinstance(options,dict):raise ValueError('無效轉檔選項')
            edge=validate(current,target,engines,options)
            if not edge['available']:raise ValueError(edge['reason'])
            clean.append({'type':'convert','target':target,'options':options});current=target
        elif step.get('type')=='tool':
            definition=tools.get(step.get('operation'))
            if not definition:raise ValueError('此工具不支援自動化流程或需額外輸入')
            if category(current) not in definition['sources'] and 'any' not in definition['sources']:raise ValueError(f'步驟 {i+1} 不接受 {current}')
            if definition['id']=='office.remove-watermark' and current not in {'docx','pptx'}:raise ValueError('只支援 DOCX／PPTX')
            params=validate_params(definition,step.get('params') or {})
            current=params.get('format') or (current if definition['output']=='source' else definition['output'])
            clean.append({'type':'tool','operation':definition['id'],'params':params})
        else:raise ValueError('無效流程步驟')
        clean[-1].update(source=before,output=current)
    on_error=config.get('onError','abort')
    if on_error not in {'abort','skip'}:raise ValueError('無效錯誤處理方式')
    return {'source':source,'target':current,'steps':clean,'onError':on_error,'name':str(config.get('name') or '未命名流程')[:120]}

def execute(job,stage,engines):
    from worker import convert,emit
    from detection import detect
    from fsutils import publish_file
    config=plan(job['workflow'],engines);current=[Path(job['sources'][0])];succeeded=0;logs=[]
    if detect(current[0],engines)['format']!=config['source']:raise ValueError('流程來源與檔案實際內容不符合')
    for i,step in enumerate(config['steps']):
        step_dir=stage/f'step-{i+1}';step_dir.mkdir();next_files=[]
        emit(i/len(config['steps'])*95,stats={'workflowStep':i+1,'workflowSteps':len(config['steps']),'phase':f'步驟 {i+1}/{len(config["steps"])}'})
        try:
            for index,source in enumerate(current):
                file_dir=step_dir/str(index);file_dir.mkdir()
                sub={'sources':[str(source)],'options':{**job.get('options',{}),**step.get('options',{})},'format':step['output']}
                if step['type']=='tool':sub.update(operation=step['operation'],params=step['params'])
                # Each adapter checks real content again; skipping a failed step cannot bypass the matrix.
                next_files.extend(convert(sub,file_dir,engines))
            if not next_files:raise ValueError('此步驟未產生檔案')
            current=next_files;succeeded+=1;logs.append({'step':i+1,'status':'completed','count':len(current)})
        except Exception as error:
            logs.append({'step':i+1,'status':'failed','error':str(error)})
            emit(stats={'workflowLog':logs,'warning':f'步驟 {i+1}：{error}'})
            if config['onError']=='abort':raise RuntimeError(f'步驟 {i+1} 失敗：{error}') from error
        emit((i+1)/len(config['steps'])*95,stats={'workflowLog':logs})
    if not succeeded:raise ValueError('流程沒有成功完成任何步驟')
    final=stage/'final';final.mkdir();result=[]
    for source in current:
        target=final/source.name
        # Publish from the private last-step directory; original input is never moved.
        if source.resolve().is_relative_to(stage.resolve()):result.append(publish_file(source,final))
        else:shutil.copy2(source,target);result.append(target)
    emit(stats={'phase':'流程完成','workflowLog':logs});return result
