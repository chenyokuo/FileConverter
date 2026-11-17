"""Decode actual native repair outputs, including linked selection audio and image edges."""
from pathlib import Path
import array,json,math,subprocess,sys
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];candidate=Path(sys.argv[1]).resolve();checks=[]
ffmpeg=str(candidate/'engines/ffmpeg/ffmpeg.exe');ffprobe=str(candidate/'engines/ffmpeg/ffprobe.exe')
def metadata(p):return json.loads(subprocess.check_output([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(p)],text=True))
def rms(p):
 samples=array.array('f');samples.frombytes(subprocess.check_output([ffmpeg,'-v','error','-ss','0.3','-i',str(p),'-t','1.2','-vn','-ar','48000','-ac','1','-f','f32le','-']))
 return math.sqrt(sum(x*x for x in samples)/len(samples))
reference=rms(ROOT/'.tools/editor-ui/red.mp4')
for label in sys.argv[2:]:
 report=json.loads((ROOT/f'test-results/{label}.json').read_text());movie,png,section=map(Path,report['outputs']);m=metadata(movie);assert abs(float(m['format']['duration'])-4)<.1
 assert {'video','audio'}<={s['codec_type'] for s in m['streams']}
 level=rms(movie);assert .85<level/reference<1.15,(label,level/reference)
 selected=metadata(report['selectedVideo']);assert abs(float(selected['format']['duration'])-2)<.1
 assert any(s['codec_type']=='audio' for s in selected['streams']);assert .85<rms(report['selectedVideo'])/reference<1.15
 for at,index in [(0.5,0),(2.5,2)]:
  rgb=subprocess.check_output([ffmpeg,'-v','error','-ss',str(at),'-i',str(movie),'-frames:v','1','-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','pipe:1']);assert rgb[index]>200 and rgb[2-index]<50
 with Image.open(png) as image:
  image.load();assert image.size==(1255,893) and image.mode=='RGBA';assert image.getpixel((0,0))[3]==0;assert image.getpixel((50,50))[0]>200;assert image.getpixel((1205,843))[2]>200
 if report.get('exifOutput'):
  with Image.open(report['exifOutput']) as oriented:
   oriented.load();assert oriented.size==(893,1255);assert oriented.getpixel((843,50))[0]>200;assert oriented.getpixel((50,1205))[2]>200
 duration=float(metadata(section)['format']['duration']);assert abs(duration-report['sectionExpectedDuration'])<.2
 checks.append({'package':label,'videoDuration':4,'videoColors':True,'audioRMSRatio':round(level/reference,4),'selectedClipDuration':2,'selectedClipAudio':True,'imageSize':[1255,893],'imageCornerPixelsAndAlpha':True,'exifSizeAndCornerPixels':[893,1255] if report.get('exifOutput') else None,'sectionDuration':duration,'publicSourceSucceeded':report.get('publicSourceSucceeded'),'ownedHLSVerified':report.get('ownedHLSVerified',False)})
result={'passed':True,'checks':checks};(ROOT/'test-results/rc2-native-content.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
