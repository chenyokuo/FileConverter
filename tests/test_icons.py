"""Verify source integrity, DPI assets, PE resources and scoped installer config."""
from pathlib import Path
import hashlib
import io
import json
import struct
import sys
import unittest
import pefile
from PIL import Image, ImageChops

ROOT=Path(__file__).resolve().parents[1]
ICONS=ROOT/'src-tauri/icons'

def pe_icons(path):
    # Installer overlays contain gigabytes of compressed runtimes; inspect only
    # the PE resource directory needed by this test, not unrelated directories.
    pe=pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    resources={}
    for kind in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if kind.id not in {3,14}:continue
        for item in kind.directory.entries:
            data=item.directory.entries[0].data.struct
            resources[kind.id,item.id]=pe.get_data(data.OffsetToData,data.Size)
    groups=[]
    for (kind,_),data in resources.items():
        if kind!=14:continue
        count=struct.unpack_from('<H',data,4)[0];offset=6+count*16
        entries=[];images=[]
        for index in range(count):
            width,height,colors,reserved,planes,bits,size,rid=struct.unpack_from('<BBBBHHIH',data,6+index*14)
            blob=resources[3,rid]
            entries.append(struct.pack('<BBBBHHII',width,height,colors,reserved,planes,bits,len(blob),offset))
            images.append(blob);offset+=len(blob)
        groups.append(b''.join([struct.pack('<HHH',0,1,count),*entries,*images]))
    pe.close()
    return groups

def verify_pe(path):
    expected=Image.open(ICONS/'icon.ico')
    groups=pe_icons(path)
    assert groups, f'No icon group in {path}'
    sizes=[]
    for group in groups:
        actual=Image.open(io.BytesIO(group))
        group_sizes=actual.ico.sizes()
        for size in group_sizes:
            a=actual.ico.getimage(size).convert('RGBA')
            b=expected.ico.getimage(size).convert('RGBA')
            assert ImageChops.difference(a,b).getbbox(alpha_only=False) is None, (path,size)
        sizes.extend(group_sizes)
    assert {(16,16),(32,32),(48,48),(256,256)}.issubset(set(sizes)), (path,sizes)
    print(f'VERIFIED PE application icons: {path.name} ({sorted(set(sizes))})')

class IconTests(unittest.TestCase):
    def test_original_integrity(self):
        manifest=json.loads((ICONS/'source/manifest.json').read_text())
        digest=hashlib.sha256((ICONS/'source/file-converter-original.png').read_bytes()).hexdigest()
        self.assertEqual(digest,'43ac05c2ceb7cd72bee21303c3ff6c1d6e905212eb3df3a1699fbc05d8b6ac77')
        self.assertEqual(manifest['sha256'],digest)
        original=Path.home()/'Downloads/高級玻璃質感檔案轉換圖示.png'
        if original.exists():self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),digest)

    def test_dpi_png_and_ico_frames(self):
        with Image.open(ICONS/'source/file-converter-original.png') as original:
            for size in (16,32,48,64,128,256,512):
                with Image.open(ICONS/f'{size}x{size}.png') as actual:
                    self.assertEqual(actual.size,(size,size))
                    expected=original.convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
                    self.assertIsNone(ImageChops.difference(actual,expected).getbbox(alpha_only=False))
            for size in (32,64,128,256,512):
                self.assertEqual((ICONS/f'{size}x{size}.png').read_bytes(),(ROOT/f'src/assets/app-icon-{size}.png').read_bytes())
        with Image.open(ICONS/'icon.ico') as ico:
            self.assertTrue({(16,16),(32,32),(48,48),(256,256)}.issubset(ico.ico.sizes()))

    def test_scoped_product_and_packaging(self):
        config=json.loads((ROOT/'src-tauri/tauri.conf.json').read_text())
        self.assertEqual(config['productName'],'File Converter')
        self.assertEqual(config['mainBinaryName'],'FileConverter')
        self.assertEqual(config['identifier'],'studio.rai.converter')
        self.assertFalse(config['bundle'].get('fileAssociations'))
        nsis=config['bundle']['windows']['nsis']
        self.assertEqual(nsis['installerIcon'],'icons/icon.ico')
        self.assertEqual(nsis['uninstallerIcon'],'icons/icon.ico')
        self.assertEqual(nsis['startMenuFolder'],'File Converter')
        self.assertNotIn('binaries/',config['bundle']['resources'])

    def test_built_executable_resources(self):
        files=[Path(p) for p in sys.argv[1:] if p.lower().endswith('.exe')]
        if not files:self.skipTest('Pass built EXE / installer paths to verify PE resources')
        for path in files:verify_pe(path)

if __name__=='__main__':
    executable_paths=sys.argv[1:]
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(IconTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
