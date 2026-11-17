"""Generate assets without changing the preserved user-provided original."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'src-tauri/icons'
SOURCE = ICONS / 'source/file-converter-original.png'
digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
with Image.open(SOURCE) as source:
    original_size = source.size
    image = source.convert('RGBA')
    side = max(image.size)
    square = Image.new('RGBA', (side, side))
    square.alpha_composite(image, ((side-image.width)//2, (side-image.height)//2))
    for size in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256, 512):
        resized = square.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(ICONS / f'{size}x{size}.png')
        if size in (32, 64, 128, 256, 512):
            assets = ROOT / 'src/assets'
            assets.mkdir(exist_ok=True)
            resized.save(assets / f'app-icon-{size}.png')
    square.save(ICONS/'icon.ico', sizes=[(s,s) for s in (16,20,24,32,40,48,64,96,128,256)])
    square.resize((256,256),Image.Resampling.LANCZOS).save(ICONS/'128x128@2x.png')
(ICONS/'source/manifest.json').write_text(json.dumps({'source': SOURCE.name, 'sha256': digest,
    'originalSize': original_size, 'resampling': 'Lanczos', 'fit': 'contain; no stretching'}, indent=2), encoding='utf-8')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == digest
print(f'Generated File Converter icons; SHA-256 {digest}')
