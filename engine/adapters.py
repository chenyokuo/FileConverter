"""Adapter interface keeps capability validation separate from existing engine code."""
from dataclasses import dataclass

@dataclass(frozen=True)
class EngineAdapter:
    name: str
    handler: str
    def execute(self, job, sources, stage, engines):
        import worker
        return getattr(worker, self.handler)(job, sources, stage, engines)

ADAPTERS = {name: EngineAdapter(name, handler) for name,handler in [
    ('pillow','convert_image'),('pymupdf','convert_pdf'),('ffmpeg','media'),('libreoffice','convert_office')]}

@dataclass(frozen=True)
class DocumentAdapter:
    name: str
    handler: str
    def execute(self,job,sources,stage,engines):
        import documents
        return getattr(documents,self.handler)(job,sources,stage,engines)
for name in ['libreoffice','pandoc','pdf2docx','pdf-text']:
    ADAPTERS[name]=DocumentAdapter(name,'convert_document')
for name in ['ghostscript','pymupdf-vector']:ADAPTERS[name]=DocumentAdapter(name,'convert_vector')
ADAPTERS['calibre']=DocumentAdapter('calibre','convert_ebook')

class ImageAdapter:
    def execute(self,job,sources,stage,engines):
        from image_engine import convert_image
        return convert_image(job,sources,stage,engines)
ADAPTERS['pillow']=ImageAdapter()
