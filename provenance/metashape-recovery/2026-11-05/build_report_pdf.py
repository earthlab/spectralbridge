"""Build the P183 evidence report from its frozen narrative and figures."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
P=Path(__file__).resolve().parent
R=P.parents[2]
data=json.loads((P/'report_sections.json').read_text())
styles=getSampleStyleSheet()
styles['BodyText'].fontName='Helvetica';styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
styles['Title'].textColor=colors.HexColor('#143c50')
styles['Heading1'].textColor=colors.HexColor('#143c50')
flow=[Paragraph('Metashape recovery',styles['Title']),Paragraph('Drone correction investigation | 6 November 2026',styles['Heading2']),Spacer(1,16),Paragraph('P183 - recovered physical evidence and remaining scientific limits',styles['BodyText']),Spacer(1,18)]
for i,(title,body) in enumerate(data['sections']):
 if i:flow.append(PageBreak())
 flow.append(Paragraph(title,styles['Heading1']))
 for para in body.split('\n\n'):flow.extend([Paragraph(escape(para),styles['BodyText']),Spacer(1,10)])
for filename,caption in data['figures']:
 path=P/'figures'/filename
 if not path.exists():continue
 flow.append(PageBreak());flow.append(Paragraph(caption.split(';')[0],styles['Heading1']))
 w,h=ImageReader(str(path)).getSize();scale=min(492/w,530/h)
 flow.extend([Spacer(1,12),Image(str(path),w*scale,h*scale),Spacer(1,14),Paragraph(escape(caption),styles['BodyText'])])
flow.append(PageBreak());flow.append(Paragraph('Technical references and evidence',styles['Heading1']))
for text,url in [('Official Python API','https://www.agisoft.com/pdf/metashape_python_api_2_3_1.pdf'),('Official footprint reconstruction example','https://github.com/agisoft-llc/metashape-scripts/blob/master/src/footprints_to_shapes.py'),('Official MicaSense reflectance workflow','https://agisoft.freshdesk.com/support/solutions/articles/31000148780-micasense-rededge-mx-processing-workflow-including-reflectance-calibration-in-agisoft-metashape-pro')]:
 flow.extend([Paragraph(f'<link href="{url}" color="#175f83">{text}</link>',styles['BodyText']),Spacer(1,12)])
flow.append(Paragraph('Local machine-readable evidence and reproducible scripts: provenance/metashape-recovery/2026-11-05. See METASHAPE_RECOVERY_REPORT.md for the complete evidence index. Vendor references establish API/encoding conventions; reported measurements are calculated from recovered project data.',styles['BodyText']))
def footer(c,doc):
 c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#526571'));c.drawString(54,30,'SpectralBridge | Experimental investigation | No production approval');c.drawRightString(558,30,str(doc.page))
out=R/'output/pdf/metashape-recovery-2026-11-06.pdf';out.parent.mkdir(exist_ok=True,parents=True)
SimpleDocTemplate(str(out),pagesize=(612,792),rightMargin=60,leftMargin=60,topMargin=48,bottomMargin=55,title='Metashape recovery and drone correction investigation',author='SpectralBridge').build(flow,onFirstPage=footer,onLaterPages=footer)
print(out)
