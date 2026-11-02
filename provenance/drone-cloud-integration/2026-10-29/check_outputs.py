"""Independent spatial, table, masking and translation checks of the real notebook run."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/private/tmp/spectralbridge-one-flight-e2e/ruby_integration_20261029_v1')
EVIDENCE = Path(__file__).resolve().parent
SOURCE = WORK / 'staged_sources/2023_AOP-Ruby-08-14-23-ExportPackage/aligned_orthomosaic.tif'
OUTPUT = WORK / 'flight_products/2023_AOP-Ruby-08-14-23-ExportPackage'
FLIGHT = OUTPUT / 'AOP_Ruby_20230814'
STEM = 'AOP_Ruby_20230814'
command = [sys.executable, str(ROOT / 'scripts/diagnose_drone_spatial_integrity.py')]
for key, path in {
    'source-tiff': SOURCE,
    'h5': FLIGHT / (STEM + '__working.h5'),
    'native': FLIGHT / (STEM + '__envi.img'),
    'corrected': FLIGHT / (STEM + '__corrected.img'),
    'final': FLIGHT / (STEM + '__landsat_like_landsat_oli_translated_envi.img'),
    'polygons': ROOT / 'Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg',
    'parquet': FLIGHT / (STEM + '__polygons.parquet'),
    'parquet-value-raster': FLIGHT / (STEM + '__corrected.img'),
    'output': EVIDENCE / 'spatial_check',
}.items():
    command.extend(['--' + key, str(path)])
command.extend(['--source-bands', '1,2,3,4,5,6,7,8,9,10', '--id-column', 'GlobalID',
                '--label', 'Ruby clean notebook: source grid and extraction validation'])
subprocess.run(command, check=True)
subprocess.run([
    sys.executable, str(ROOT / 'provenance/drone-spatial-integrity/2026-10-29/validate_ruby_outputs.py'),
    '--source', str(SOURCE), '--result', str(OUTPUT / 'pipeline_result.json'),
    '--output', str(EVIDENCE / 'full_pixel_checks.json'),
], check=True)
