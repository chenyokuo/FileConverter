"""Download pinned FFmpeg release into ignored vendor directory. No runtime downloads."""
import hashlib
import json
import pathlib
import shutil
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = 'db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec'

def main():
    dest = ROOT / 'vendor' / 'ffmpeg'
    dest.mkdir(parents=True, exist_ok=True)
    # Gyan's immutable release archive; this GPL build contains libx264/libx265.
    url = 'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.1.2-essentials_build.zip'
    archive = ROOT / '.tools' / 'ffmpeg-8.1.2.zip'
    archive.parent.mkdir(exist_ok=True)
    if not archive.exists():
        partial=archive.with_suffix('.download')
        urllib.request.urlretrieve(url, partial)
        partial.replace(archive)
    with archive.open('rb') as source: digest=hashlib.file_digest(source,'sha256').hexdigest()
    if digest!=EXPECTED_SHA256:raise RuntimeError('FFmpeg archive checksum mismatch; do not execute this download')
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            if member.endswith(('/ffmpeg.exe', '/ffprobe.exe', '/LICENSE', '/LICENSE.txt')):
                with z.open(member) as source, (dest / pathlib.Path(member).name).open('wb') as target:
                    shutil.copyfileobj(source, target)
    manifest = {'url': url, 'archive_sha256': digest,
                'license': 'GPL-3.0-or-later; see THIRD_PARTY_NOTICES.md',
                'files': {p.name: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest() for p in dest.glob('*.exe')}}
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
