"""Short illustrated result packet; experimental status remains visible throughout."""
import csv,json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from PIL import Image as PILImage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OUT=ROOT/'output/pdf/drone-camera-rerun-2026-11-05.pdf';OUT.parent.mkdir(parents=True,exist_ok=True)
configs=json.loads((HERE/'site_inputs.json').read_text());qa=json.loads((HERE/'qa_summary.json').read_text());verified=json.loads((HERE/'verification.json').read_text())
metrics=list(csv.DictReader((HERE/'native_all_band_metrics.csv').open()));shared=list(csv.DictReader((HERE/'shared_all_ten_band_metrics.csv').open()))
styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='AuditTitle',fontName='Helvetica-Bold',fontSize=23,leading=28,spaceAfter=13,textColor=colors.HexColor('#123d4b')));styles.add(ParagraphStyle(name='AuditBody',fontSize=10.5,leading=14,spaceAfter=9));styles.add(ParagraphStyle(name='AuditSmall',fontSize=9,leading=12,spaceAfter=7));styles.add(ParagraphStyle(name='AuditCell',fontSize=9.2,leading=12))
story=[]

def para(s,style='AuditBody'):return Paragraph(s,styles[style])
def add(s):story.append(para(s))
def page(title,label=None):
    if story:story.append(PageBreak())
    if label:story.append(para(label.upper(),'AuditSmall'))
    story.append(para(title,'AuditTitle'))
def table(rows,widths):
    t=Table([[para(escape(str(v)),'AuditCell') for v in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e1eef2')),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cddfe4'))]));story.extend([t,Spacer(1,10)])
def image(name,width=712):
    path=HERE/'figures'/name
    with PILImage.open(path) as im:w,h=im.size
    story.append(Image(str(path),width=width,height=width*h/w));story.append(Spacer(1,6))
def footer(canvas,doc):
    canvas.saveState();canvas.setFillColor(colors.HexColor('#546e7a'));canvas.setFont('Helvetica',8);canvas.drawString(38,17,'SpectralBridge | 5 November 2026 | EXPERIMENTAL - not production approved');canvas.drawRightString(754,17,str(doc.page));canvas.restoreState()

def value(site,stage,nm,key,pop='native'):
    row=next(r for r in (metrics if pop=='native' else shared) if r['site']==site and r['stage']==stage and int(r['wavelength_nm'])==nm)
    return float(row[key])

page('Three-site drone camera rerun','Gordon | Goldhill | Ruby - 5 November 2026')
add('<b>Result:</b> all three sites were rerun with the supplied camera locations. Gordon and Goldhill produced topographic-only, BRDF-only and combined experimental imagery. Ruby produced topographic-only imagery; its BRDF and combined branches were rejected by unchanged prediction checks.')
table([['Site','Topographic only','BRDF only','Combined'],['Gordon','Executed experimental','Executed experimental','Executed experimental'],['Goldhill','Executed experimental','Executed experimental','Executed experimental'],['Ruby','Executed experimental','Not supported','Not supported']],[90,205,205,212])
add('Seven native corrected GeoTIFFs and matching ENVI products were generated. Camera files and source rasters remain unchanged. The original 10 cm, fixed-range 0-10,000 preparation was reused, with no scene min/max adjustment.')
add('<b>These are conditional experiments.</b> They reuse the earlier Goldhill DN/32768 interpretation and nadir/center-weighted contributor scenario. Physical calibration, actual orthomosaic contributors, camera/world convention, vertical datum and clock zone remain unverified. Numerical acceptance is not independent physical validation.')
add('<b>Two important findings:</b> Ruby photo tags support August 15 rather than the manifest August 16 date. Goldhill still declares EPSG:5070; this run explicitly records the previously evidenced EPSG:26913 interpretation without editing the CSV.')
add('Goldhill also retains large conditional correction tails. This report preserves those values and their source locations; visual smoothness is not treated as proof of safe correction.')

page('Inputs, clocks and coordinate interpretation','1 | Source evidence')
table([['Site','Photo rows / positions','Matched photo-clock interval','Solar midpoint used'],*[[c['site'],f"{c['camera_metadata']['photo_rows']:,} / {c['camera_position_count']:,}",c['photo_clock_start']+' to '+c['photo_clock_end'][11:],c['solar_datetime']] for c in configs]],[75,135,275,227])
add('Every camera PhotoID matched exactly one original SD1/SD2 image-metadata record. All three solar fields use the existing package NOAA helper at that matched midpoint, with UTC retained as an explicit, unverified clock scenario. No timestamp or date was inferred from the folder name.')
table([['Input check','Outcome'],['Camera CSVs','Three refreshed/checksummed from summer-2023; declared row counts, finite positions and proper rotations validated'],['CRS','Gordon/Ruby: EPSG:26913. Goldhill: source says5070; project/DEM report and footprint evidence support explicit26913 interpretation'],['Terrain','Summer-2023 sidecars were25cm and rejected for this grid. Six10cm sidecars exactly match the prior verified terrain hashes'],['Sensor/footprint','Each report lists1280x960,5.5mm focal length and3.75um pixels; nadir/flight-heading footprint is still a scenario'],['Radiometry','Stored DN*10000/65535 is numerical preparation. Experimental multiplier65535/(10000*32768) does not certify calibration']],[125,587])
add('Ruby uses the available spatially clipped original-package export. Cameras outside that clipped ground footprint remain potential contributors; they are not dropped solely because their centers lie outside the crop.')

for name in ['Gordon','Goldhill','Ruby']:
    page(name+': raw and correction branches','2 | Consistent displays within each site')
    image(name.lower()+'_stages.png')
    story.append(para('Top: RGB650/560/475nm. Middle:650nm red. Bottom:717nm red edge. Fixed display scales are shared across branches and sites; no display limit changes analytical values. White areas denote unavailable/unsupported data. Ruby rejected branches are explicitly not produced.','AuditSmall'))

page('Candidate rays and topographic support','3 | Geometry is reconstructed, not observed mosaic membership')
image('gordon_support.png');image('goldhill_support.png')
story.append(para('Nadir rectangular footprints define potential contributors. The BRDF design blends individual shared-kernel values with the established center weights; it is not the kernel of an averaged angle. The central-candidate angle shown here is diagnostic. Orange topographic cells are unsupported and remain NoData.','AuditSmall'))

page('Why Ruby stopped at BRDF','4 | Rejection is a result, not a missing output to fill')
image('ruby_support.png')
table([['Branch','Invalid wavelengths','Recorded reason'],['BRDF only','444,475,650,668nm','Nonpositive or cancellation/uncertainty-dominated model prediction'],['Combined','650,668nm','Same unchanged prediction/uncertainty checks; all-band output not accepted']],[125,175,412])
add('For the combined650nm fit, the design has rank3 and condition number about464. The conditional reference prediction is0.01229 with spatial-cluster standard error0.00939. Its uncertainty does not resolve a positive correction reference. Rank alone is insufficient; the recorded fit uses60 spatial groups, not1.8million independent observations.')
add('No identity image or partial-band product was substituted as a successful BRDF result. Native/topographic products and invalid model diagnostics are retained for review. The full Ruby combined workflow therefore remains incomplete.')

page('Large tails remain visible','5 | Native versus shared-support populations')
image('native_vs_shared_extremes.png')
story.append(para('Native maxima include every finite output observation. Shared bars use one mask requiring all ten bands in every available accepted stage for that site. Ruby shared support covers raw/topography only; it is not a completed BRDF population. Removing unsupported cells changes the population and cannot alone demonstrate scientific improvement.','AuditSmall'))

page('What changed, and what did not','6 | Quantitative review of red and red-edge results')
table([['Site / available combined branch','650nm raw / output maximum','717nm raw / output maximum','Largest650nm factor'],*[[name+(' / topography' if name=='Ruby' else ' / combined'),f"{value(name,'raw',650,'maximum'):.4f} / {value(name,'topographic_only' if name=='Ruby' else 'combined',650,'maximum'):.4f}",f"{value(name,'raw',717,'maximum'):.4f} / {value(name,'topographic_only' if name=='Ruby' else 'combined',717,'maximum'):.4f}",f"{value(name,'topographic_only' if name=='Ruby' else 'combined',650,'factor_maximum'):.2f}x"] for name in ['Gordon','Goldhill','Ruby']]],[195,180,180,157])
add('All numbers above use the unverified DN/32768 fractional interpretation, not independently calibrated reflectance. Goldhill combined native red reaches2.4243 and717nm reaches1.7714; the maximum red factor is21.55x. These are review-worthy tails, not values silently clipped to a plausible range.')
add('On Goldhill shared all-ten-band support, those maxima are1.5568 and0.6895. Both native and common-support results are retained.140 bounded extreme source records identify exact row/column, raw value, corrected value, factor, support membership and source/product path.')
image('polygon_stage_comparison.png')
story.append(para('The302 established half-diameter polygon identities and200,363 pixel memberships are preserved. Per-stage support differs. These10,360 compact polygon-band summaries are experimental diagnostics, not an approved physical spectral library or evidence of ecological gain.','AuditSmall'))

page('Verification, reuse and the remaining boundary','7 | Concrete products without a production-completion claim')
table([['Site','Geometry-covered ground pixels','All-ten-band common support','Exact finite output values'],*[[c['site'],f"{json.loads((HERE/(c['site'].lower()+'_geometry.json')).read_text())['covered_pixels']:,}",f"{next(r['common_all_bands_available_stage_pixels'] for r in qa if r['site']==c['site']):,}",f"{sum(p.get('finite_values_compared',0) for p in next(r['products'] for r in verified if r['site']==c['site'])):,}"] for c in configs]],[95,205,205,207])
add('Every accepted GeoTIFF matches its ENVI values exactly in bounded windows, including missing-data positions. Grids, projected CRS and wavelengths remain aligned with the prepared inputs. The raw candidate matches the prepared TIFF exactly. Original/derived input hashes and frozen implementation hashes were checked after execution.')
add('Geometry and correction checkpoints were rerun and reused only after signature and output-hash checks. The inherited production radiometry gate still rejects the hypothetical calibration; every experimental header is rejected by the approved-library gate.49 focused geometry/correction regression tests passed.')
add('This uses the same shared correction driver, RossThick/LiDenseR math and conditioned SCS+C policy as the earlier Goldhill experiment, through its existing isolated research boundary. Production globals were not patched, no new calibration was asserted and no method was tuned to force Ruby to pass.')
add('<b>Still pending:</b> independently supported physical calibration/contributors and resolution of Ruby BRDF support. Approved translation/library generation and completed-site production uploads were not performed. No old raster, camera CSV, shared field manifest or previous scientific result was overwritten.')
add('Products: archive/local/drone-camera-rerun/2026-11-05/photo_clock_v1/&lt;site&gt;/. Compact evidence/figures: provenance/drone-camera-rerun/2026-11-05/. See DRONE_CAMERA_RERUN_REPORT.md for exact paths, source provenance and reproducible commands.')

SimpleDocTemplate(str(OUT),pagesize=(792,612),leftMargin=40,rightMargin=40,topMargin=30,bottomMargin=33,title='Three-Site Drone Camera Rerun - Gordon, Goldhill and Ruby',author='SpectralBridge').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
