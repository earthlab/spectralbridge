"""Build the requested report, explicitly separating available stages from E2E."""
import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUTPUT=ROOT/'output/pdf'
OUTPUT.mkdir(parents=True,exist_ok=True)
PDF=OUTPUT/'spectralbridge-drone-three-site-validation.pdf'
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleSmall',fontName='Helvetica-Bold',fontSize=24,leading=29,textColor=colors.HexColor('#153b4c'),spaceAfter=20))
styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=10))
styles.add(ParagraphStyle(name='CaptionCustom',fontName='Helvetica',fontSize=8.5,leading=12,textColor=colors.HexColor('#455a64'),spaceAfter=10))
styles.add(ParagraphStyle(name='CellCustom',fontName='Helvetica',fontSize=8.5,leading=12))
story=[]

def p(text,style='BodyCustom'):return Paragraph(text,styles[style])
def add(text):story.append(p(text))
def title(text,kicker=None):
    if story:story.append(PageBreak())
    if kicker:story.append(p(kicker.upper(),'CaptionCustom'))
    story.append(p(text,'TitleSmall'))
def table(rows,widths):
    t=Table([[p(escape(str(c)),'CellCustom') for c in row] for row in rows],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eff3')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#7695a1')),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#dbe4e8'))]))
    story.append(t);story.append(Spacer(1,12))
def fig(name,width=500):
    from PIL import Image as PILImage
    path=HERE/'figures'/name
    with PILImage.open(path) as im:w,h=im.size
    story.append(Image(str(path),width=width,height=width*h/w));story.append(Spacer(1,10))
def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor('#dbe4e8'));canvas.line(42,39,570,39)
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#455a64'))
    canvas.drawString(42,26,'SpectralBridge | Three-site integration | 4 November 2026')
    canvas.drawRightString(570,26,f'{doc.page}');canvas.restoreState()

summary=json.loads((HERE/'diagnostic_summary.json').read_text())
manifest={s:json.loads((HERE/f'{s.lower()}_source_manifest.json').read_text()) for s in ['Gordon','Goldhill','Ruby']}
verification=json.loads((HERE/'available_product_verification.json').read_text()) if (HERE/'available_product_verification.json').exists() else []
rows=list(csv.DictReader((HERE/'all_band_numeric_diagnostics.csv').open()))

title('SpectralBridge Drone Pipeline:<br/>Three-Site End-to-End Validation','Available-stage validation | location tables pending')
add('<b>Decision: available source stages completed; full end-to-end validation remains incomplete.</b> Gordon, Goldhill and Ruby original-package imagery was discovered in CyVerse, downloaded with remote checksum verification and prepared at 10 cm. Existing production code created working HDF5 and ENVI products and standard QA. New camera-location tables were explicitly deferred by the user.')
add('All three requested production runs, with both corrections and translation enabled, stopped at the physical-calibration gate. The original integer image values cannot yet be certified as physical reflectance. This is a documented scientific limitation, not evidence that a correction algorithm failed.')
table([['Verified available work','Result'],['Source packages / transferred inputs','3 packages / 48 files'],['Prepared imagery','10 spectral bands at 10 cm for every site'],['Spatial polygon support','302 half-diameter polygons; 200,363 indexed pixels'],['Physical corrections / translation / approved libraries','Not completed; no scientific acceptance bypass'],['Production uploads','Not attempted: no fully validated completed site']],[200,300])
add('This report evaluates source handling and numerical preparation. It cannot answer whether BRDF or topographic correction introduces harmful artifacts because no eligible corrected products were generated in this run.')
add('Software: 2.3.0rc2; preparation branch codex/prepare-2.3.0rc2. Baseline commit bb3da46bea0a4295ca3152a9f607ed17140575f1 with recorded working-tree edits. Earlier Goldhill research products are not relabeled as results of this integration test.')

title('What was discovered','1 | Live Data Store evidence')
add('The intake listed actual contents under /iplant/home/shared/earthlab/macrosystems/field-data/uas-packages. It selected original-package ORTHO exports and retained associated reports, metadata and terrain alternatives. It did not use historical normalized 10 cm imagery as the radiometric source.')
table([['Site','Selected orthomosaic','Native size'],*[ [s,Path(m['original_local']['path']).name,' x '.join(map(str,m['original_local']['shape']))+' pixels'] for s,m in manifest.items()]],[60,310,130])
add('<b>Ruby coverage qualification:</b> the only selected original-package orthomosaic is ORTHO_CLIPPED. It is a spatially clipped export; this test does not establish that an unclipped original was available.')
add('Gordon uses a different date/name spelling from Goldhill. Discovery handles that variation and case-insensitive site names. More than one acceptable ORTHO candidate produces an ambiguity report instead of an automatic choice.')
add('The associated SD1/SD2 image-metadata tables were preserved as source metadata. They were not substituted for the new location tables. Point-cloud archives were not downloaded because the available stages do not require them.')
add('Remote MD5 checksums were compared using their actual algorithm. Logical Data Store paths, byte sizes and local SHA-256/MD5 records are preserved in each source manifest. Physical server replica paths are never used as inputs.')

title('Source validation and preparation','2 | What the numbers mean')
table([['Property','Finding'],['Raster geometry','All three: projected NAD83 / UTM zone 13N, north-up, east-right, unrotated'],['Spectral contract','11 UInt16 bands: 10 signal bands plus declared alpha band 11'],['Wavelengths','444, 475, 531, 560, 650, 668, 705, 717, 740, 862 nm'],['Wavelength evidence','Established package convention; TIFF files have no independent wavelength declarations'],['Native pixel size','Gordon 8.063 cm; Goldhill 8.443 cm; Ruby 8.315 cm'],['Prepared grid','10 cm; existing recorded grids used only for spatial comparison support'],['Numerical conversion','stored = DN x 10000 / 65535; offset 0; no min/max adjustment'],['Physical conversion','Unknown: numeric range alone does not certify reflectance']],[145,355])
add('Bilinear resampling excludes source alpha/NoData; the footprint mask is resampled with nearest neighbor. Individual missing spectral bands remain missing without erasing observed bands. Zero is retained unless explicitly declared missing. Source files remain unchanged.')
add('<b>Terrain warning:</b> Goldhill has distinct DTM.tif and dtm.tif objects. Stable separate local directories now prevent case collisions. The uppercase terrain raster opens; the tiny lowercase file does not open as a valid raster despite matching its remote checksum. It was retained and marked invalid, not repaired or adopted.')
add('Preparation works one spectral band at a time, with source/target masks in memory. RAM scales with raster area; it is not a window-bounded resampler. HDF5 and ENVI conversion continue to use the existing chunked pipeline.')

for s in ['Gordon','Goldhill','Ruby']:
    title(s+': original and prepared imagery','3 | Source diagnostics, not correction acceptance')
    fig(s.lower()+'_maps.png')
    story.append(p('Top: native original. Bottom: 10 cm preparation. RGB uses 650/560/475 nm and a fixed square-root stretch. Red (650 nm) and red-edge (717 nm) maps share a fixed 0-16,384 DN-equivalent scale. Both rows share map limits. Display sampling does not alter analytical statistics.','CaptionCustom'))
    sub=[r for r in rows if r['site']==s and r['stage']=='Prepared 10 cm' and r['wavelength_nm'] in {'650','717'}]
    table([['Band','Valid pixels','Median DN equivalent','1st / 99th percentile'],*[[r['wavelength_nm']+' nm',f"{int(r['valid']):,}",f"{float(r['median']):,.1f}",f"{float(r['p01']):,.1f} / {float(r['p99']):,.1f}"] for r in sub]],[65,110,145,180])
    add('The broad scene structures remain visible after preparation. This side-by-side check is descriptive: it does not establish physical calibration, eliminate all possible source seams, or validate correction factors. No topographic-only, BRDF-only or combined corrected result exists for this integration run.')

title('All-band and cross-site diagnostics','4 | Full-pixel numerical evidence')
fig('all_band_distributions.png')
add('Solid lines show the median of every finite prepared pixel in each band; dashed lines show native-source medians. The shaded range is the prepared interquartile range. Prepared values are converted back to original DN equivalent solely to compare numeric distributions. Site differences must not be interpreted as calibrated sensor or vegetation differences.')
table([['Site','10 cm raster support','Valid 650 nm pixels','Prepared/native median change'],*[[s,' x '.join(map(str,manifest[s]['prepared']['shape'][:2])),f"{int(next(r['valid'] for r in rows if r['site']==s and r['stage']=='Prepared 10 cm' and r['wavelength_nm']=='650')):,}",f"{100*(float(next(r['median'] for r in rows if r['site']==s and r['stage']=='Prepared 10 cm' and r['wavelength_nm']=='650'))/float(next(r['median'] for r in rows if r['site']==s and r['stage']=='Native original' and r['wavelength_nm']=='650'))-1):+.2f}%"] for s in manifest]],[70,125,130,175])
add('The accompanying CSV contains all ten bands, both grids, valid/missing counts, minima, maxima, percentiles and 99th-percentile adjacent-pixel jumps in both directions. Native and prepared populations differ through resampling and spatial support; changes in their summaries are not a pixel-by-pixel radiometric calibration residual.')
add('<b>Artifact conclusion:</b> harmful correction artifacts are not evaluable. A zero raw-versus-identity difference in standard QA simply confirms that no correction was requested in the preparation run.')

title('Polygon support without calibration claims','5 | Researcher identities retained')
fig('polygon_signals.png')
table([['Site','Half-diameter polygons','Indexed pixel centers'],*[[s['site'],s['polygon_count'],f"{s['polygon_pixels']:,}"] for s in summary['sites']]],[120,180,200])
add('The existing polygon-index utility retains polygon attributes, source references and pixel-center coordinates. Each curve is a polygon median signal. These descriptive DN summaries are explicitly marked DESCRIPTIVE_DN_NOT_APPROVED_LIBRARY. They are not approved reflectance libraries, calibrated vegetation signatures or translated products.')
add('The source is the established half-diameter GeoPackage. Full-diameter polygons were not substituted. Polygon IDs, recorded site/cover/PFT attributes and provenance remain attached to the index and compact diagnostic table.')

title('The actual production result','6 | No silent scientific substitution')
table([['Stage','All three sites'],['Discovery / download / source validation','Completed for selected orthomosaics; terrain alternatives assessed'],['10 cm preparation / working H5 / ENVI','Completed; restart reuse exercised'],['Standard preparation QA','Generated; physical scientific status NOT_EVALUATED'],['Topographic correction','Requested; blocked before application by unverified radiometry'],['BRDF correction / reconstructed geometry','Requested; same earlier gate; new location tables deferred'],['Combined correction / translation','No eligible corrected input; not produced'],['Approved spectral libraries','Not produced; existing acceptance requirements preserved'],['Production upload / remote output verification','Not attempted because no site completed the required production validation']],[185,315])
add('<b>Exact first blocking reason:</b> Radiometry UNSUPPORTED: authoritative physical scale, offset, units and provenance required (Original UInt16 DN; fixed numerical encoding; physical calibration unavailable).')
add('No viewing-angle maps, kernel conditioning, illumination support or correction-factor distributions are reported as observed results. These depend on inputs/stages that did not complete. The standard blocked-run QA summary records the reason; source-only QA figures remain separately scoped.')
add('The new location tables are deferred by user instruction. Their future validator requires finite camera positions, unique identifiers, timestamp syntax, explicit projected metre CRS and overlap with the raster. It does not auto-relabel CRS or certify vertical datum, clock zone, orientation or mosaic contributors.')

title('Reproducibility and next steps','7 | Readiness assessment')
add('<b>Integration defects repaired:</b> actual JSON listing/checksum handling; stable case-distinct local staging; source-only QA scientific status; restart of an explicitly uncorrected identity product without falsely requiring physical correction provenance. Requested correction gates remain active.')
add('Checksummed source/configuration/output preparation records support restart. The real pipeline reuses working HDF5 and ENVI stages. All 48 staged inputs were checked against their remote identities and exercised through offline reuse with downloads forbidden. Exact prepared-to-ENVI comparisons check every finite value and missing-data position in bounded windows.')
if verification:
    table([['Site','Verified inputs','Exact finite ENVI values'],*[[r['site'].title(),r['verified_inputs'],f"{r['finite_values_compared']:,}"] for r in verification]],[120,160,220])
add('<b>BLOCKER for the full objective:</b> no scientifically eligible corrected production chain and therefore no completed production upload. <b>IMPORTANT:</b> unreadable lowercase Goldhill terrain alternative and post-freeze source changes requiring replacement release-artifact validation. <b>DEFER:</b> user-pending camera tables, independent physical calibration and actual contributor validation; these are scientific/input limitations, not automatically algorithm defects.')
add('To resume: supply validated location tables and an accepted radiometric scale/offset with provenance; align and validate terrain/geometry through existing contracts; rerun both corrections, translation and approved-library extraction; evaluate all correction stages and upload only a completed, validated site to a new Data Store directory. Verify remote checksums before declaring end-to-end success.')
add('The archived RC2 wheel/sdist predate these integration edits. Their earlier test results apply to those exact bytes. A replacement candidate must be built and tested before publication. No release, tag, merge or production upload was performed here.')
add('Evidence: provenance/drone-three-site-integration/2026-11-04. Large local inputs, prepared TIFFs and pipeline outputs: archive/local/drone-three-site-integration/2026-11-04. See DRONE_THREE_SITE_INTEGRATION_REPORT.md for commands, validation results and an inventory of deliverables.')

SimpleDocTemplate(str(PDF),pagesize=(612,792),rightMargin=56,leftMargin=56,topMargin=42,bottomMargin=54,title='SpectralBridge Drone Pipeline: Three-Site End-to-End Validation',author='SpectralBridge integration validation').build(story,onFirstPage=footer,onLaterPages=footer)
print(PDF)
