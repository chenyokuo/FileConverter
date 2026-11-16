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
