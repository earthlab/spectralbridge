"""Compose a print-size poster from the unchanged vector manuscript synthesis."""
import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = ROOT / 'output/pdf/results_poster/SpectralBridge_Results_Poster.pdf'
SOURCE = ROOT / 'output/figures/manuscript_synthesis/figure_main_synthesis.pdf'
CAPTION = SOURCE.with_name('figure_main_synthesis_caption.txt')
W, H = 36 * 72, 48 * 72
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=(W, H))
c.setTitle('SpectralBridge | Reading vegetation through spectra')
c.setAuthor('SpectralBridge | Earth Lab')
c.setSubject('Existing manuscript results; synthetic abundance experiments, not field validation')
ink, teal, muted = '#183440', '#327C70', '#536774'
c.setFillColor(HexColor('#F3F5F1'))
c.rect(0, 0, W, H, fill=1, stroke=0)

def text(x, y, s, size, color=ink, bold=False):
    c.setFillColor(HexColor(color))
    c.setFont('Helvetica-Bold' if bold else 'Helvetica', size)
    c.drawString(x, y, s)

text(108, H-93, 'S P E C T R A L B R I D G E   /   E A R T H  L A B', 25, teal, True)
text(108, H-193, 'Reading vegetation', 87, bold=True)
text(108, H-288, 'through spectra', 87, bold=True)
text(111, H-341, 'Distinct spectral signatures. Uneven transfer. Ambiguous mixtures.', 32, muted)
# White figure field and generous print margins.
fw = 28.7 * 72
src = PdfReader(SOURCE).pages[0]
scale = fw / float(src.mediabox.width)
fh = float(src.mediabox.height) * scale
fx = (W-fw)/2
fy = 214
c.setFillColor(HexColor('#FFFFFF'))
c.roundRect(fx-30, fy-18, fw+60, fh+36, 20, fill=1, stroke=0)
text(108, 150, 'THE TAKEAWAY', 23, teal, True)
text(108, 108, 'Spectral differences support recognition; lower mixture error does not establish unique composition.', 26, bold=True)
text(108, 70, 'Abundance panels use controlled synthetic fractions. Independent field validation and physical-unit checks remain outstanding.', 23, muted)
text(108, 32, 'Source: manuscript synthesis, panels A-F | earthlab/spectralbridge | Curated 27 October 2026', 18, muted)
c.showPage()
c.save()
page = PdfReader(buf).pages[0]
page.merge_transformed_page(src, Transformation().scale(scale).translate(fx, fy))
writer = PdfWriter()
writer.add_page(page)
writer.add_metadata({'/Title': 'SpectralBridge | Reading vegetation through spectra', '/Author': 'SpectralBridge | Earth Lab', '/Subject': '36 x 48 inch vector results poster; internal retrospective and synthetic evidence'})
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('wb') as f:
    writer.write(f)
checks = PdfReader(OUT)
assert len(checks.pages) == 1
assert tuple(float(v) for v in checks.pages[0].mediabox) == (0., 0., float(W), float(H))
assert 'Independent field validation' in checks.pages[0].extract_text()
assert fy+fh < H-360
manifest = {'output': str(OUT.relative_to(ROOT)), 'size_inches': [36, 48], 'vector_source_preserved': True, 'new_scientific_analysis': False, 'sources': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, CAPTION)}, 'output_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(), 'checks': ['one page', '36 x 48 inches', 'caveat text present', 'figure below title']}
(BASE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(OUT)
