"""Render the real exported PDF for visual inspection; no report images are generated."""
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'evidence/Report-concise.pdf'
OUT=ROOT/'evidence/report-render';OUT.mkdir(exist_ok=True)
document=pdfium.PdfDocument(PDF)
for i in range(len(document)):
    document[i].render(scale=1.5).to_pil().save(OUT/f'page-{i+1}.png')
for start in range(0,len(document),4):
    contact=Image.new('RGB',(1000,1340),'#e2e2e2');draw=ImageDraw.Draw(contact)
    for offset in range(4):
        index=start+offset
        if index>=len(document):break
        page=Image.open(OUT/f'page-{index+1}.png');page.thumbnail((480,625))
        x=(offset%2)*500+10;y=(offset//2)*670+25
        contact.paste(page,(x,y));draw.text((x,y-18),f'Page {index+1}',fill='black')
    contact.save(OUT/f'contact-{start//4+1}.png')
reader=PdfReader(PDF)
for i,page in enumerate(reader.pages):
    text=page.extract_text()
    print(i+1,len(text),text.replace('\n',' ')[:105],text.replace('\n',' ')[-90:])
