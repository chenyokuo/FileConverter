# Third-party notices and distribution obligations

Research date: 2026-11-16. The application source is AGPL-3.0-or-later, selected to accommodate the open-source PyMuPDF engine. A private repository does **not** remove source-disclosure obligations when distributing binaries. For a proprietary distribution, obtain appropriate Artifex licensing and review all bundled dependencies. No commercial license is included.

| Component | Selected version | License / source |
|---|---|---|
| Tauri Rust | 2.12.5 | MIT OR Apache-2.0, https://github.com/tauri-apps/tauri |
| Tauri JS API / CLI | 2.12.4 | MIT OR Apache-2.0 |
| Tauri dialog | 2.8.4 | MIT OR Apache-2.0 |
| infer | 0.22.0 (direct, pinned; previously transitive) | MIT, https://github.com/bojand/infer |
| window-vibrancy | 0.8.1 | MIT OR Apache-2.0 |
| React / React DOM | 19.3.1 | MIT, https://github.com/facebook/react |
| Vite / React plugin | 8.3.8 / 6.3.0 | MIT, https://github.com/vitejs/vite |
| TypeScript | 7.0.2 | Apache-2.0, https://github.com/microsoft/TypeScript |
| Tailwind CSS | 4.3.5 | MIT, https://github.com/tailwindlabs/tailwindcss |
| Motion for React | 14.14.0 | MIT, https://github.com/motiondivision/motion |
| Radix Dialog | 1.3.1 | MIT, https://github.com/radix-ui/primitives |
| Lucide React | 1.73.0 | ISC, https://github.com/lucide-icons/lucide |
| Inter / Noto Sans TC | Fontsource 5.3.0 / 5.3.1 | SIL OFL-1.1; bundled locally, no Google Fonts requests |
| Pillow | 13.0.0 | MIT-CMU / HPND, https://github.com/python-pillow/Pillow |
| PyMuPDF / MuPDF | 2.1 | AGPL-3.0-or-later OR commercial, https://pymupdf.io/licensing |
| Python | build host 3.13 | PSF license, https://docs.python.org/3/license.html |
| PyInstaller | 6.22.3 | GPL-2.0-or-later with bootloader exception, https://pyinstaller.org/en/stable/license.html |
| FFmpeg Gyan essentials | 8.1.2 | GPL-3.0-or-later build, https://www.gyan.dev/ffmpeg/builds/ |
| LibreOffice (app-local runtime) | 26.8.3 | MPL-2.0, LGPL and other component licenses, https://www.libreoffice.org/about-us/licenses/ |
| Playwright (development tests only) | 1.65.1 | Apache-2.0, https://github.com/microsoft/playwright |
| Prettier (development formatting only) | 3.10.1 | MIT, https://github.com/prettier/prettier |

The official registries were queried before choosing versions. npm and Cargo lockfiles pin transitive dependencies. `engine/requirements-lock.txt` records the Python environment used for packaging. React Bits, Magic UI, Rive, Lottie and extra animation libraries are intentionally omitted: Motion and CSS cover the actual interactions. UI primitives are local shadcn-style components using Radix Dialog, not an unneeded CLI dependency.

## Binary distributions

The build script copies npm license files, Python package license metadata, this notice, and the project license to `release/licenses/`. Keep those with Portable builds. Tauri's installer includes the notices and project license. Frozen Python dependency metadata is included in the sidecar. Generate a Cargo license inventory before public distribution and preserve the Rust dependency notices as well.

The selected FFmpeg build enables GPL codecs including libx264 / libx265. Do not describe it as an LGPL-only distribution. Preserve its license, build configuration (`ffmpeg -buildconf`), exact release URL and archive hash (`vendor/ffmpeg/manifest.json`). Corresponding source, configuration and applicable scripts must be made available under the relevant GPL terms when distributing it. Build/source references: https://github.com/GyanD/codexffmpeg and https://ffmpeg.org/download.html . Before distributing to others, prepare a complete corresponding-source package for the exact binary; links alone are not a substitute for satisfying the license.

Official guidance: https://ffmpeg.org/legal.html . FFmpeg's LGPL checklist applies to LGPL builds; this project's selected build is GPL. PyMuPDF preserves producer metadata in generated PDFs; the worker does not strip it. See https://pymupdf.readthedocs.io/en/latest/about.html .

LibreOffice is bundled app-locally, with its own LICENSE/NOTICE and runtime DLLs. Microsoft WebView2 Fixed Version 157.0.4341.60 is bundled without changing the system Runtime; its binaries remain subject to Microsoft redistribution terms. Windows installers are unsigned unless the builder supplies a signing certificate through their own secure environment.

## Release gate

Local development / private evaluation builds are provided. Public or customer redistribution requires a complete license inventory and corresponding-source delivery, code signing as appropriate, and clean-machine installation testing. No licensing review or clean-machine certification is implied by a successful compile.

## Application artwork

The File Converter application icon was supplied locally by the project owner. Its preserved original and SHA-256 manifest are in `src-tauri/icons/source/`. Tauri Icon Generator produced platform assets; `scripts/icons.py` reproducibly generates Windows multi-size ICO and density-aware PNG assets using Pillow Lanczos without changing the original. No permission to reuse unrelated trademarks or artwork is implied. Only this application uses these assets; no system file associations or other applications are changed.

## P1 runtime additions

Pinned acquisition sources and binary/model SHA-256 values are recorded in `engine-lock.json`. LibreOffice 26.8.3 is staged app-locally (MPL/LGPL and component licenses), Calibre 9.18.0 (GPL-3.0-or-later), Pandoc 3.14 (GPL-2.0-or-later), Ghostscript 10.08.0 (AGPL-3.0-or-later), 7-Zip 25.01 (LGPL with unRAR restriction), Deno 2.9.8 (MIT), and Tesseract fast eng/chi_tra models (Apache-2.0). These are separate local executables/resources, not system installations. Final redistribution inventories and corresponding-source requirements are checked in P5.

Python additions: pillow-heif 1.8.1 (BSD-3-Clause wrapper; binary wheel includes LGPL-3.0 libheif/libde265 and GPL-2.0-or-later x265, plus MinGW runtime notices), pdf2docx 0.5.13 (MIT; upstream no longer actively maintained by Artifex), OpenCV headless 5.0.0.93 (Apache-2.0 and bundled-library notices), pypdf 7.1.0 (BSD), pypdfium2 5.15.2 (BSD/Apache and PDFium notices), python-docx 1.2.0, python-pptx 1.0.2 and openpyxl 3.1.5 (MIT). PyMuPDF remains AGPL/commercial; the application remains AGPL-3.0-or-later. Exact transitive versions are in the Python lockfile. No proprietary licensing grant is claimed.

## P3/P4/P5 runtime and distribution audit

- yt-dlp 2026.10.26: Unlicense library; transitive optional dependencies retain their licenses. yt-dlp-ejs 0.8.0 and bundled Deno run only the explicit network feature. No standalone third-party yt-dlp EXE with a different aggregate license is used.
- Tauri single-instance 2.5.5: MIT OR Apache-2.0.
- Noto Sans CJK TC Sans2.004: OFL-1.1, locally bundled for image watermark text. UI font files remain Fontsource OFL copies.
- WebView2 Fixed Version 157.0.4341.60: Microsoft runtime redistribution terms; app-local, unmodified, Microsoft Authenticode signature checked. Download URL and CAB SHA-256 in engine-lock.json.
- x265 4.3 source header explicitly permits GPL version 2 or later: https://github.com/Multicorewareinc/x265/blob/4.3/source/x265.h . Do not describe the pillow-heif binary wheel as merely BSD. The AGPL application uses the compatible later-version terms.
- 7-Zip unRAR restriction applies to decoding RAR; File Converter does not create RAR.

The P5 collector preserves actual runtime license files, Python wheel bundled-library notices, local npm/Rust notices, engine binary hashes, and FFmpeg build configuration. It also inventories development packages; presence in that inventory does not mean an excluded AI module is shipped. No AI model/runtime is intentionally bundled.

This is an unsigned private evaluation release candidate, not a completed customer-distribution clearance. Before onward binary distribution, provide recipients with this application's complete source and build instructions and a complete corresponding-source delivery for the exact GPL/AGPL/LGPL components, including FFmpeg codec/build dependencies, Calibre, Pandoc, Ghostscript and linked codec libraries. The current repository and upstream links do not by themselves constitute a complete corresponding-source archive for all external binary builds. Private GitHub visibility does not waive that obligation. See docs/DISTRIBUTION.md for the remaining release gate.

The NSIS template is copied from Tauri CLI 2.12.4 commit 993038c49185307dfc895ab7657d77ca0d5ed7c7 (MIT OR Apache-2.0); its exact upstream URL/hash is preserved in src-tauri/windows/installer.nsi.hbs. The Solid compression flag is removed and datablock deduplication is disabled to avoid large-payload mapping and search costs; NSIS uses zlib compression.


## Multimedia expansion (1.1.0-rc.1)

No Fabric/Vidstack/AI SDK or model was added. The editor viewport uses existing React, SVG/Pointer Events and HTML video; rendering uses existing Pillow, FFmpeg and the packaged Noto CJK font. Tauri protocol-asset adds http-range 0.1.6 (MIT), locked by Cargo. All Python setup is an explicit 40-package core whitelist with Windows CPython 3.13 wheel SHA-256, excluding optional PyMuPDF layout/LLM/ONNX packages. The official PyMuPDF wheel itself also carries optional layout/LLM directories. Setup removes only these unused directories from its explicitly owned new venv, preserving the official cached wheel, package metadata and license files. New classic build environments are then checked to contain none of those AI modules/models. Original development environments can contain unrelated older packages; only selected frozen runtime modules are shipped.

The verified 7-Zip 25.01 bootstrap/download artifacts are preparation tools, not system installation or file-association changes. Exact URLs, hashes, architecture and payload destinations are in engine-lock.json and config/python-wheels.json. Existing corresponding-source distribution requirements in docs/DISTRIBUTION.md remain applicable; private candidate testing does not constitute commercial redistribution clearance.
