"""Opt-in live public-site smoke through the actual shipping frozen sidecar."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import time

from test_engine import Client

ROOT = Path(__file__).resolve().parents[1]
candidate = Path(sys.argv[1]).resolve()
report = {"url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
          "frozenSidecar": True, "started": time.time(), "status": "not-run"}
os.environ["PATH"] = os.environ["SystemRoot"] + r"\System32;" + os.environ["SystemRoot"]
os.environ["FILE_CONVERTER_TEST_FROZEN"] = str(candidate / "binaries/FileConverterEngine/FileConverterEngine.exe")
os.environ["FILE_CONVERTER_TEST_ENGINES"] = str(candidate / "engines")
with tempfile.TemporaryDirectory(prefix="youtube-packaged-", dir=ROOT / ".tools") as scratch:
    client = Client(Path(scratch) / "data")
    job = None
    try:
        info = client.call("analyze_url", {"url": report["url"]})
        entry = info["entries"][0]
        choice = next(str(f["format_id"]) for f in entry["formats"]
                      if f.get("ext") == "mp4" and f.get("acodec") not in {None, "none"}
                      and f.get("vcodec") not in {None, "none"} and (f.get("height") or 0) <= 480)
        report.update(title=entry["title"], duration=entry["duration"], formats=len(entry["formats"]), chosenFormat=choice)
        job = client.call("enqueue_download", {"analysisId": info["analysisId"], "outputDir": str(Path(scratch) / "out"),
            "items": [{"key": entry["key"], "formatId": choice, "sections": [{"start": 1, "end": 2.5}],
                       "precise": True, "convertTo": "mp4"}]})[0]
        result = client.wait([job["id"]], timeout=120)[0]
        assert result["status"] == "completed", result.get("error")
        metadata = json.loads(subprocess.check_output([str(candidate / "engines/ffmpeg/ffprobe.exe"), "-v", "error",
            "-show_format", "-of", "json", result["outputs"][0]], text=True))
        duration = float(metadata["format"]["duration"])
        assert abs(duration - 1.5) < .2, duration
        report.update(status="passed", outputDuration=duration)
    except Exception as error:
        report.update(status="restricted-or-failed", error=str(error)[-2000:])
    finally:
        if job:
            client.call("cancel", {"id": job["id"]})
            client.wait([job["id"]], timeout=20)
        client.close()
        report["finished"] = time.time()
        (ROOT / "test-results/youtube-packaged.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
sys.exit(0 if report["status"] == "passed" else 1)
