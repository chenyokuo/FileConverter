"""Tool dispatcher shares validation and the same isolated queue as conversion."""
from pathlib import Path
from tool_catalog import validate_tool

def execute(job,stage,engines):
    sources=[Path(p) for p in job['sources']]
    definition,params=validate_tool(job['operation'],job.get('params',{}),sources,engines)
    job=dict(job,params=params)
    op=job['operation']
    if job.get('previewOnly') and op=='video.delogo':
        from worker import probe
        duration=float(probe(sources[0],engines['ffprobe']).get('format',{}).get('duration') or 0)
        job['options']={**job.get('options',{}),'trimStart':0,'trimEnd':min(10,duration) if duration else 0}
    if op.startswith('pdf.'):
        from pdf_tools import execute as handler
    elif op=='image.metadata' or op.startswith(('office.','files.')):
        from file_tools import execute as handler
    elif op.startswith('image.'):
        from image_engine import execute_tool as handler
    elif op.startswith(('video.','audio.')):
        from media_tools import execute as handler
    elif op.startswith('archive.'):
        from archives import execute as handler
    else:raise ValueError('Tool handler unavailable')
    return handler(job,sources,stage,engines)
