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
| LibreOffice (separately installed) | detected from local install | MPL-2.0, LGPL and other component licenses, https://www.libreoffice.org/about-us/licenses/ |
| Playwright (development tests only) | 1.65.1 | Apache-2.0, https://github.com/microsoft/playwright |
| Prettier (development formatting only) | 3.10.1 | MIT, https://github.com/prettier/prettier |

The official registries were queried before choosing versions. npm and Cargo lockfiles pin transitive dependencies. `engine/requirements-lock.txt` records the Python environment used for packaging. React Bits, Magic UI, Rive, Lottie and extra animation libraries are intentionally omitted: Motion and CSS cover the actual interactions. UI primitives are local shadcn-style components using Radix Dialog, not an unneeded CLI dependency.

## Binary distributions

The build script copies npm license files, Python package license metadata, this notice, and the project license to `release/licenses/`. Keep those with Portable builds. Tauri's installer includes the notices and project license. Frozen Python dependency metadata is included in the sidecar. Generate a Cargo license inventory before public distribution and preserve the Rust dependency notices as well.

The selected FFmpeg build enables GPL codecs including libx264 / libx265. Do not describe it as an LGPL-only distribution. Preserve its license, build configuration (`ffmpeg -buildconf`), exact release URL and archive hash (`vendor/ffmpeg/manifest.json`). Corresponding source, configuration and applicable scripts must be made available under the relevant GPL terms when distributing it. Build/source references: https://github.com/GyanD/codexffmpeg and https://ffmpeg.org/download.html . Before distributing to others, prepare a complete corresponding-source package for the exact binary; links alone are not a substitute for satisfying the license.

Official guidance: https://ffmpeg.org/legal.html . FFmpeg's LGPL checklist applies to LGPL builds; this project's selected build is GPL. PyMuPDF preserves producer metadata in generated PDFs; the worker does not strip it. See https://pymupdf.readthedocs.io/en/latest/about.html .

LibreOffice is not bundled in this build. Its detection does not grant redistribution rights to user-installed components or fonts. Microsoft WebView2 offline installer is distributed using Tauri's supported mode and remains subject to Microsoft's runtime terms. Windows installers are unsigned unless the builder supplies a signing certificate through their own secure environment.

## Release gate

Local development / private evaluation builds are provided. Public or customer redistribution requires a complete license inventory and corresponding-source delivery, code signing as appropriate, and clean-machine installation testing. No licensing review or clean-machine certification is implied by a successful compile.

## Application artwork

The File Converter application icon was supplied locally by the project owner. Its preserved original and SHA-256 manifest are in `src-tauri/icons/source/`. Tauri Icon Generator produced platform assets; `scripts/icons.py` reproducibly generates Windows multi-size ICO and density-aware PNG assets using Pillow Lanczos without changing the original. No permission to reuse unrelated trademarks or artwork is implied. Only this application uses these assets; no system file associations or other applications are changed.
