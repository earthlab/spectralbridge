"""Exact native products, immutable inputs and enforced experimental-library gates."""
import json
from pathlib import Path
import numpy as np
import rasterio
from spectralbridge.envi import hdr_to_dict
from spectralbridge.radiometry import require_library_header
from prepare_rerun import HERE,WORK,sha,write
rows=[]
for config in json.loads((HERE/'site_inputs.json').read_text()):
    folder=WORK/config['site'].lower();completed=json.loads((folder/'corrections_complete.json').read_text())
    for path,digest in config['input_sha256'].items():
        if sha(path)!=digest:raise AssertionError('Input changed: '+path)
    for relative,digest in config['implementation_sha256'].items():
        if sha(HERE.parents[2]/relative)!=digest:raise AssertionError('Runtime changed during experiment: '+relative)
    for path,digest in completed['output_sha256'].items():
        if sha(path)!=digest:raise AssertionError('Output changed: '+path)
    with rasterio.open(config['prepared']) as raw:
        shape,crs,transform=raw.shape,raw.crs,raw.transform
        with rasterio.open(folder/(config['flight_stem']+'__experimental_candidate.img')) as candidate:
            assert candidate.shape==shape and candidate.crs==crs and candidate.transform.almost_equals(transform,precision=1e-8)
            for _,window in raw.block_windows(1):
                a=raw.read(window=window,masked=True).filled(np.nan);b=candidate.read(window=window,masked=True).filled(np.nan)
                np.testing.assert_array_equal(a,b)
    products=[]
    for record in completed['branches']:
        if record['status']!='EXECUTED_EXPERIMENTAL':
            products.append(dict(branch=record['branch'],status=record['status'],reason=record['reason']));continue
        header=hdr_to_dict(Path(record['header']))
        assert header['radiometry status']=='HYPOTHETICAL_UNVERIFIED' and header['scientific validation status']=='EXPERIMENTAL'
        try:require_library_header(header)
        except ValueError as exc:gate=str(exc)
        else:raise AssertionError('Experimental product unexpectedly accepted into physical library')
        finite=0
        with rasterio.open(record['image']) as envi,rasterio.open(record['geotiff']) as native:
            assert envi.shape==native.shape==shape and envi.count==native.count==10
            assert envi.crs==native.crs==crs and envi.transform.almost_equals(transform,precision=1e-8) and native.transform==transform
            for _,window in native.block_windows(1):
                a=envi.read(window=window);b=native.read(window=window)
                np.testing.assert_array_equal(a,b)
                finite+=int(np.isfinite(a).sum())
        assert record['audit']['topo_applied']==(record['branch']!='brdf_only')
        assert record['audit']['brdf_applied']==(record['branch']!='topographic_only')
        products.append(dict(branch=record['branch'],status=record['status'],native_envi_exact=True,finite_values_compared=finite,library_gate_rejection=gate,topographic_applied=record['audit']['topo_applied'],brdf_applied=record['audit']['brdf_applied']))
    rows.append(dict(site=config['site'],original_and_derived_inputs_unchanged=True,implementation_frozen=True,raw_candidate_exact_prepared=True,products=products))
    print(config['site'],'immutable source, native value/grid equality and experimental gate verified',flush=True)
write(HERE/'verification.json',rows)
