"""White package overview poster; existing real images are illustrative only."""
from pathlib import Path
import hashlib
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
IMAGES=BASE.parent/'flightline_revision'
OUT=ROOT/'output/pdf/results_poster/SpectralBridge_Package_Poster.pdf'
W,H=2592,3456
INK='#183440';MUTED='#526873';TEAL='#176E65';RULE='#D9E5E4';PALE='#F4F8F7'
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('SpectralBridge | From flightlines to analysis-ready data')
c.setAuthor('SpectralBridge | Earth Lab')
c.setSubject('Core package functions: processing, correction, sensor-like products, exports, quality checks, bulk and library analysis')
c.setFillColor(HexColor('#FFFFFF'));c.rect(0,0,W,H,fill=1,stroke=0)
boxes=[]
def text(x,y,s,size=30,color=INK,bold=False,font=None):
    font=font or ('Helvetica-Bold' if bold else 'Helvetica')
    tw=stringWidth(s,font,size)
    assert 0<=x and x+tw<W-70,(s,x+tw)
    assert 0<y<H-size
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,y,s)
    boxes.append([x,y,tw,size,s])
def line(x1,y1,x2,y2,color=RULE,width=2):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.line(x1,y1,x2,y2)
def marker(x,y):
    c.setFillColor(HexColor('#FFFFFF'));c.setStrokeColor(HexColor(TEAL));c.setLineWidth(4)
    c.circle(x,y,25,fill=1,stroke=1)
    c.setFillColor(HexColor(TEAL));c.setFont('Helvetica-Bold',27);c.drawCentredString(x,y-10,'A')

text(108,3344,'E A R T H  L A B   /   S C I E N T I F I C  P Y T H O N',25,TEAL,True)
text(108,3200,'SpectralBridge',124,bold=True)
text(112,3110,'From flightlines to analysis-ready data',62,bold=True)
text(112,3045,'Prepare and compare reflected light across airborne, drone and sensor-like products.',34,MUTED)

# Large real-data examples remain supporting illustrations, not a before/after claim.
text(108,2954,'REAL FLIGHTLINE  /  VISIBLE LIGHT',26,TEAL,True)
text(1450,2954,'A flightline is the strip recorded along one flight path.',26,MUTED)
ix,iw=108,2376
ih=iw*1115/5351
for name,iy in [('visible',2420),('near_infrared',1790)]:
    c.drawImage(str(IMAGES/(name+'.png')),ix,iy,width=iw,height=ih,mask='auto')
    marker(ix+iw*.698,iy+ih*.73)
text(108,2323,'SAME GROUND  /  INFRARED SHOWN IN RED',26,TEAL,True)
text(1450,2323,'A marks the same patch in both images.',26,MUTED)
text(108,1726,'Infrared reveals contrasts our eyes miss. Red is a display color, not heat or fire.',31,MUTED)
text(108,1677,'Illustration: two views of one corrected image, not a before-and-after correction test.',27,MUTED)

text(108,1578,'What the package does',54,bold=True)
text(108,1523,'The NEON workflow turns a spectral image into reusable scientific products.',31,MUTED)

cards=[
 (108,1120,'01','Prepare flightlines',
  ['Download NEON data and export spectral images.',
   'Use a separate route for supported local drone files.'],
  'Readable images + metadata'),
 (1344,1120,'02','Correct viewing effects',
  ['Account for terrain and viewing geometry',
   'with BRDF and topographic correction.'],
  'Corrected spectral images'),
 (108,735,'03','Make sensor-like products',
  ['Combine wavelengths using configured sensor bands,',
   'including Landsat and MicaSense representations.'],
  'Configured target-band images'),
 (1344,735,'04','Export and check',
  ['Extract pixel or polygon tables, merge outputs,',
   'and inspect quality plots, metrics and reports.'],
  'Parquet tables + quality evidence'),
]
for x,y,num,title,body,output in cards:
    cw,ch=1140,340
    c.setFillColor(HexColor(PALE));c.roundRect(x,y,cw,ch,18,fill=1,stroke=0)
    text(x+32,y+270,num,34,TEAL,True)
    text(x+112,y+270,title,39,bold=True)
    for j,s in enumerate(body):
        assert stringWidth(s,'Helvetica',30)<cw-64
        text(x+32,y+196-j*46,s,30,MUTED)
    line(x+32,y+109,x+cw-32,y+109)
    text(x+32,y+58,output,29,TEAL,True)

text(108,649,'Choose the workflow that fits your data',42,bold=True)
routes=[
 (108,'NEON flightlines',['Process one flight or a collection.'],'go_forth_and_multiply'),
 (726,'Local drone imagery',['Process supported TIFF/HDF5.'],'run_drone_pipeline'),
 (1344,'Completed products',['Compare flights with compact statistics.'],'run_bulk_pipeline'),
 (1962,'Spectral libraries',['Inspect inputs and report patterns.'],'run_spectral_library_analysis'),
]
for x,title,desc,api in routes:
    text(x,580,title,31,TEAL,True)
    for j,s in enumerate(desc):text(x,535-j*37,s,25,MUTED)
    text(x,486,api,20,MUTED,font='Courier')

line(108,438,2484,438)
text(108,381,'Built for long runs',35,bold=True)
text(540,381,'Reuse valid outputs. Work in chunks. Keep files and provenance traceable.',30,MUTED)
text(108,307,'Sensor-like products support comparison; agreement with independent observations still needs validation.',27,MUTED)
text(108,249,'Explore the documentation',29,TEAL,True)
text(108,202,'earthlab.github.io/spectralbridge',29)
c.linkURL('https://earthlab.github.io/spectralbridge/',(108,196,1050,232),relative=0)
text(1420,249,'github.com/earthlab/spectralbridge',28,TEAL,True)
c.linkURL('https://github.com/earthlab/spectralbridge',(1420,242,2460,282),relative=0)
text(108,136,'Image: NEON R10C, 15 September 2021 | Native 1 m pixels | Original footprint in both views',23,MUTED)
text(108,94,'Display only: per-channel 2-98% contrast stretch, gamma 0.8. White outside the flightline means no image data.',22,MUTED)
text(108,52,'Visible RGB near 650/550/470 nm; infrared RGB near 850/650/550 nm | Package source and local docs | 27 October 2026',21,MUTED)
c.showPage();c.save()
r=PdfReader(OUT)
assert len(r.pages)==1
assert list(map(float,r.pages[0].mediabox))==[0.,0.,float(W),float(H)]
t=r.pages[0].extract_text()
for s in ['Prepare flightlines','Correct viewing effects','Make sensor-like products','Export and check','run_drone_pipeline','run_bulk_pipeline','run_spectral_library_analysis','independent observations','not a before-and-after']:assert s in t,s
sources=[ROOT/'README.md',ROOT/'src/spectralbridge/__init__.py',ROOT/'docs/pipeline.md',ROOT/'docs/vignettes/bulk-analysis.md',ROOT/'docs/vignettes/spectral-library.md',IMAGES/'visible.png',IMAGES/'near_infrared.png',IMAGES/'imagery_manifest.json']
(BASE/'manifest.json').write_text(json.dumps({'output':str(OUT.relative_to(ROOT)),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'size_inches':[36,48],'background':'white','image_dpi':5351/(iw/72),'source_flights':1,'views':2,'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'checks':['one page','36 x 48 inches','required functions and caveats present','text within page/card widths'],'scientific_analysis_rerun':False},indent=2)+'\n')
(BASE/'layout_boxes.json').write_text(json.dumps(boxes,indent=2)+'\n')
print(OUT)
