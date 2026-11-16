# Offline engines

Never commit executables here. `scripts/prepare.py` downloads pinned engine dependencies and records versions/hashes in the local release manifest. FFmpeg and ffprobe go under `vendor/ffmpeg/`; a frozen Python worker under `src-tauri/binaries/`. LibreOffice is detected separately and is not silently claimed as bundled.
