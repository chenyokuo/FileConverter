"""Generate owned 120-second low-resolution media for the range UI test."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from runtime import locate,command
engines=locate(ROOT/'vendor');target=ROOT/'.tools/range-preview.mp4'
target.parent.mkdir(exist_ok=True)
if not target.exists():command([engines['ffmpeg'],'-v','error','-f','lavfi','-i','testsrc2=s=320x180:r=10:d=120','-f','lavfi','-i','sine=frequency=440:duration=120','-c:v','libx264','-preset','ultrafast','-c:a','aac','-movflags','+faststart','-shortest',target])
