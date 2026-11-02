"""Build novice-facing poster from native-resolution, display-only flight composites."""
from pathlib import Path
import hashlib
import io
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
OUT=ROOT/'output/pdf/results_poster/SpectralBridge_Flightline_Poster.pdf'
W,H=2592,3456
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('SpectralBridge | A different light on the same landscape')
c.setAuthor('SpectralBridge | Earth Lab')
c.setSubject('Three annotated views of one real NEON R10C flightline, 15 September 2021')
BG='#0B1822';WHITE='#F5F6F1';MUTED='#BACBD1';TEAL='#75E1CF';ORANGE='#FFB26B'
c.setFillColor(HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
boxes=[]
def text(x,y,s,size=28,color=WHITE,bold=False):
    font='Helvetica-Bold' if bold else 'Helvetica'
    assert x+stringWidth(s,font,size)<W-65,(s,'text too wide')
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,y,s)
    boxes.append([x,y,stringWidth(s,font,size),size,s])
def line(x1,y1,x2,y2,color=TEAL,width=3):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.line(x1,y1,x2,y2)
def target(x,y,n):
    c.setFillColor(HexColor(BG));c.setStrokeColor(HexColor(TEAL));c.setLineWidth(3)
    c.circle(x,y,23,fill=1,stroke=1)
    c.setFillColor(HexColor(WHITE));c.setFont('Helvetica-Bold',25);c.drawCentredString(x,y-9,str(n))
def arrow(x1,y1,x2,y2):
    import math
    line(x1,y1,x2,y2)
    a=math.atan2(y2-y1,x2-x1)
    for da in [-.45,.45]:
        line(x2,y2,x2-18*math.cos(a+da),y2-18*math.sin(a+da))

text(108,3343,'S P E C T R A L B R I D G E   /   E A R T H  L A B',25,TEAL,True)
text(108,3225,'A different light',106,bold=True)
text(108,3110,'on the same landscape',106,bold=True)
text(112,3038,'An aircraft measures more colors of light than our eyes can see.',35,MUTED)
text(112,2990,"A flightline is the strip of ground recorded along the aircraft's path.",35,MUTED)

ix,iw=108,2376
ih=iw*1115/5351
rows=[
 ('01','Start with a familiar view','Visible light: red + green + blue, similar to a color photograph.','visible',2878,2300),
 ('02','Reveal invisible light','Near-infrared light is shown in red. Vegetated areas often stand out.','near_infrared',2048,1470),
 ('03','Switch the infrared channels','Shortwave infrared is shown in red; near-infrared is shown in green.','shortwave_infrared',1218,640),
]
for n,title,sub,name,ty,iy in rows:
    text(108,ty,n,48,TEAL,True)
    text(212,ty,title,48,bold=True)
    text(212,ty-57,sub,32,MUTED)
    c.drawImage(str(BASE/(name+'.png')),ix,iy,width=iw,height=ih,mask='auto')
# Corresponding point in every image, no invented geographic classification.
for iy in [2300,1470,640]:
    px=ix+iw*.698;py=iy+ih*(1-.27)
    target(px,py,'B')
# Road reference point in visible image.
px=ix+iw*.40;py=2300+ih*(1-.377)
target(px,py,'A')
arrow(560,2252,px-26,py-18)
text(108,2225,'A  A straight road helps you match the views.',29,TEAL,True)
text(1450,2225,'B  Follow this same patch in all three images.',29,TEAL,True)
text(108,2176,'Dark background lies outside the flightline; it is not a land-cover color.',28,MUTED)
line(108,2134,2484,2134,'#29414D',2)
text(108,1398,'B  This patch appears bright red in this view.',31,TEAL,True)
text(108,1351,'Red is a display choice here. It does not mean heat or fire.',30,MUTED)
line(108,1304,2484,1304,'#29414D',2)
text(108,568,'B  The same patch now appears green.',31,TEAL,True)
text(108,521,'The ground has not changed: we changed which light becomes each screen color.',30,MUTED)
line(108,464,2484,464,'#29414D',2)
text(108,392,'ONE FLIGHT. THREE WAYS TO SEE IT.',34,TEAL,True)
text(108,341,'SpectralBridge helps researchers process airborne light measurements and compare',31)
text(108,296,'landscapes across wavelengths and sensor scales.',31)
text(108,223,'Read the colors as clues, not a map of plant species or a measurement of plant health.',27,MUTED)
text(108,168,'Real NEON imagery | R10C | 15 September 2021 | Native 1 m pixels | Same footprint in every view',24,MUTED)
text(108,124,'Colors enhanced for visibility: each channel uses a 2-98% contrast stretch and gamma 0.8.',23,MUTED)
text(108,82,'Selected bands near 650/550/470 nm; 850/650/550 nm; 1650/850/650 nm (screen red/green/blue).',22,MUTED)
text(108,40,'Source: archived BRDF/topographic-corrected flightline | earthlab/spectralbridge | Curated 27 October 2026',20,MUTED)
c.showPage();c.save()
r=PdfReader(OUT)
assert len(r.pages)==1
assert list(map(float,r.pages[0].mediabox))==[0.,0.,float(W),float(H)]
t=r.pages[0].extract_text()
for label in ['not mean heat or fire','ONE FLIGHT','2-98%','Same footprint']:assert label in t
(BASE/'layout_boxes.json').write_text(json.dumps(boxes,indent=2)+'\n')
(BASE/'poster_manifest.json').write_text(json.dumps({'output':str(OUT.relative_to(ROOT)),'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'size_inches':[36,48],'effective_image_dpi':5351/(iw/72),'source_flights':1,'views':3,'native_pixels':[5351,1115],'checks':['one page','36 x 48 inches','novice caveats present','text within horizontal bounds'],'scientific_analysis_rerun':False},indent=2)+'\n')
print(OUT)
