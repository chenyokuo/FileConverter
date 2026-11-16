"""Explicit, deliberately bounded format compatibility matrix."""
IMAGE = {'jpg', 'jpeg', 'png', 'webp', 'bmp', 'tif', 'tiff'}
VIDEO = {'mp4', 'mov', 'mkv', 'avi', 'webm', 'm4v'}
AUDIO = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'opus'}
OFFICE = {
    'docx': ['pdf', 'odt', 'docx', 'rtf', 'txt'], 'odt': ['pdf', 'docx', 'odt', 'rtf', 'txt'],
    'doc': ['pdf', 'docx', 'odt', 'rtf', 'txt'], 'rtf': ['pdf', 'docx', 'odt', 'txt'],
    'xlsx': ['pdf', 'ods', 'xlsx', 'csv'], 'ods': ['pdf', 'xlsx', 'ods', 'csv'], 'xls': ['pdf', 'xlsx', 'ods', 'csv'],
    'pptx': ['pdf', 'odp', 'pptx'], 'odp': ['pdf', 'pptx', 'odp'], 'ppt': ['pdf', 'pptx', 'odp'],
}

def category(ext):
    if ext in IMAGE: return 'image'
    if ext in VIDEO: return 'video'
    if ext in AUDIO: return 'audio'
    if ext == 'pdf': return 'pdf'
    if ext in OFFICE: return 'office'
    return 'unsupported'

def outputs(ext):
    kind = category(ext)
    if kind == 'image': return ['png', 'jpg', 'webp', 'bmp', 'tiff', 'pdf']
    if kind == 'video': return ['mp4', 'mov', 'mkv', 'avi', 'webm', 'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'opus']
    if kind == 'audio': return ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'opus']
    if kind == 'pdf': return ['png', 'jpg', 'pdf']
    return OFFICE.get(ext, [])
