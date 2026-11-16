"""Create the project's original geometric R mark with Pillow."""
from pathlib import Path
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]/'src-tauri'/'icons'
root.mkdir(parents=True,exist_ok=True)
image=Image.new('RGBA',(512,512));draw=ImageDraw.Draw(image)
draw.rounded_rectangle((8,8,504,504),radius=112,fill='#4f8cff')
draw.polygon([(145,119),(281,119),(357,161),(357,251),(298,292),(376,394),(283,394),(213,293),(213,394),(145,394)],fill='white')
draw.polygon([(213,182),(270,182),(288,194),(288,230),(270,242),(213,242)],fill='#4f8cff')
image.save(root/'icon.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
for size in [32,128,256]:image.resize((size,size),Image.Resampling.LANCZOS).save(root/f'{size}x{size}.png')
