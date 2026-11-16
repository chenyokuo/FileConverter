"""Small, original fixtures for the native UI harness; never commit generated files."""
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]/'.tools/ui-fixtures'
root.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(1600,1000));draw=ImageDraw.Draw(image)
for y in range(1000):
    t=y/1000;draw.line((0,y,1600,y),fill=(int(25+35*t),int(38+28*t),int(80+40*t)))
draw.ellipse((650,-500,2100,950),fill='#78678e')
draw.ellipse((-700,400,1150,1800),fill='#244f63')
draw.ellipse((750,650,2000,1900),fill='#1b354c')
image.save(root/'玻璃背景 測試.png')
Image.new('RGBA',(400,240),(90,150,240,160)).save(root/'中文 alpha & 測試.png')
