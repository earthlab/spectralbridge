"""Catalog available products and preserve precise deferred-stage status."""
import json
import shutil
from pathlib import Path
import pandas as pd
from spectralbridge.remote import file_checksums
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORK=ROOT/'archive/local/drone-three-site-integration/2026-11-04'
field=pd.read_csv(ROOT/'src/spectralbridge/data/drone_field_manifest.csv')
ledger=[]
for site in ['Gordon','Goldhill','Ruby']:
    p=HERE/f'{site.lower()}_source_manifest.json'
    m=json.loads(p.read_text())
    acquisition=field[field.Plot.astype(str).str.contains(site,case=False,regex=False)]
    m['acquisition_metadata_rows']=acquisition.astype(object).where(pd.notnull(acquisition),None).to_dict('records')
    m['acquisition_time_zone']='UTC configuration for existing manifest interpretation; not independently verified clock zone'
    m['filename_date_warning']='Flight stem preserves package provenance; package filename date is not an independently verified acquisition date'
    p.write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
    output=WORK/'outputs'/m['flight_stem']
    (output/'source_manifest.json').write_text(p.read_text())
    stages=[('discovery','COMPLETE'),('verified_download','COMPLETE'),('orthomosaic_validation','COMPLETE_WITH_SCIENTIFIC_LIMITATIONS'),('numeric_10cm_preparation','COMPLETE'),('working_hdf5','COMPLETE'),('raw_envi','COMPLETE'),('half_diameter_polygon_index','COMPLETE'),('source_only_standard_qa','COMPLETE_SCIENTIFICALLY_NOT_EVALUATED'),('camera_table_validation','DEFERRED_BY_USER'),('topographic_correction','BLOCKED_RADIOMETRY'),('brdf_correction','BLOCKED_RADIOMETRY_AND_DEFERRED_GEOMETRY'),('combined_correction','DEPENDENCY_BLOCKED'),('translation','DEPENDENCY_BLOCKED'),('approved_spectral_library','DEPENDENCY_BLOCKED'),('corrected_artifact_assessment','NOT_EVALUABLE'),('production_upload','NOT_ATTEMPTED_INCOMPLETE_SITE'),('remote_output_integrity','NOT_ATTEMPTED')]
    ledger.extend(dict(site=site,stage=stage,status=status) for stage,status in stages)
(HERE/'stage_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
catalog=[]
for directory in [WORK/'prepared',WORK/'outputs']:
    for path in sorted(directory.rglob('*')):
        if path.is_file() and '.part' not in path.name:
            catalog.append(dict(path=str(path.relative_to(WORK)),size_bytes=path.stat().st_size,**file_checksums(path)))
(HERE/'available_output_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
for source,name in [('/private/tmp/p177-available-verified.log','available_stages.log'),('/private/tmp/p177-intake-final.log','intake.log'),('/private/tmp/p177-product-verification.log','product_verification.log')]:
    if Path(source).exists():shutil.copyfile(source,HERE/name)
print(len(catalog),'files cataloged;',sum(r['size_bytes'] for r in catalog),'bytes')
