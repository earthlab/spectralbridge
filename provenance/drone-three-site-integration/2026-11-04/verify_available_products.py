"""Verify original checksums, offline transfer reuse and exact ENVI values."""
import json
from pathlib import Path
import numpy as np
import rasterio
from spectralbridge.remote import checksum_matches,file_checksums
from spectralbridge.drone_production import stage_original_drone_package
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORK=ROOT/'archive/local/drone-three-site-integration/2026-11-04'
class NoDownload:
    def download_file(self,*args,**kwargs):raise AssertionError('Valid input was unnecessarily downloaded')
rows=[]
for site in ['gordon','goldhill','ruby']:
    selection=json.loads((HERE/f'{site}_remote_selection.json').read_text())
    staged=stage_original_drone_package(selection,staging_dir=WORK/'inputs',backend=NoDownload())
    assert all(r['status']=='reused' and r['remote_checksum_verified'] for r in staged['transfers'])
    manifest=json.loads((HERE/f'{site}_source_manifest.json').read_text())
    out=WORK/'outputs'/manifest['flight_stem']
    prep=json.loads((out/'preparation_pipeline_result.json').read_text())
    assert prep['status']=='complete' and prep['qa_summary']['scientific_qa_status']=='not_evaluated'
    target=json.loads((out/'requested_pipeline_result.json').read_text())
    assert target['status']=='incomplete' and len(target['blocked'])==1 and not target['failed']
    raw=next((out/'preparation_pipeline').rglob('*__envi.img'))
    count=0
    with rasterio.open(manifest['prepared']['output']) as src,rasterio.open(raw) as dst:
        assert src.shape==dst.shape and src.count==dst.count==10
        assert src.crs==dst.crs and src.transform.almost_equals(dst.transform,precision=1e-8)
        for _,window in src.block_windows(1):
            a,b=src.read(window=window,masked=True),dst.read(window=window,masked=True)
            av,bv=a.filled(np.nan),b.filled(np.nan)
            np.testing.assert_array_equal(np.isfinite(av),np.isfinite(bv))
            np.testing.assert_array_equal(av,bv)
            count+=int(np.isfinite(av).sum())
    original=Path(manifest['original_local']['path'])
    assert file_checksums(original)['sha256']==manifest['original_local']['sha256']
    assert checksum_matches(original,selection['orthomosaic']['checksum'])
    rows.append(dict(site=site,verified_inputs=len(staged['transfers']),all_transfers_reused=True,
        original_unchanged=True,raw_envi_exact=True,finite_values_compared=count,
        preparation_execution_status=prep['status'],scientific_qa_status=prep['qa_summary']['scientific_qa_status'],
        production_status=target['status'],blocking_reason=target['blocked'][0]['error']))
    print(site,rows[-1],flush=True)
(HERE/'available_product_verification.json').write_text(json.dumps(rows,indent=2)+'\n')
