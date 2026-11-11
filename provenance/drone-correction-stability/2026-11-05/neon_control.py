"""Actual NEON window before/after regression; no experimental calibration adapter."""
import importlib.util,sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'provenance/goldhill-clean-source-brdf/2026-11-03'))
from common import NEON,WAVES,sha
from spectralbridge import corrections as after
from spectralbridge.neon_cube import NeonCube
from spectralbridge.envi_writer import EnviWriter,finalize_scientific_header
from spectralbridge.radiometry import library_radiometry
import rasterio
path=HERE/'reproduced_baseline/source_corrections.py';spec=importlib.util.spec_from_file_location('spectralbridge._p182_neon_before',path);before=importlib.util.module_from_spec(spec);sys.modules[spec.name]=before;spec.loader.exec_module(before)
work=ROOT/'archive/local/drone-correction-stability/2026-11-05/neon_control';work.mkdir(parents=True,exist_ok=True)
cube=NeonCube(NEON,line_slice=(350,470),sample_slice=(1000,4000));selected=np.array([np.argmin(abs(cube.wavelengths-w)) for w in WAVES]);cube.data=cube.data[...,selected].copy();cube.wavelengths=cube.wavelengths[selected];cube.bands=10
if cube.fwhm is not None:cube.fwhm=cube.fwhm[selected]
original=cube.data.copy();results=[]
for topo in [False,True]:
 images=[]
 for label,mod in [('before',before),('after',after)]:
  folder=work/(label+('_combined' if topo else '_brdf'));path=mod.fit_and_save_brdf_model(cube,folder,brdf_kernel_config=mod.HYTOOLS_BRDF_KERNEL_CONFIG,apply_topography=topo);model=json.loads(path.read_text());assert model['validation']['status']=='VALID'
  data=mod.apply_topo_correct(cube,cube.data,0,cube.lines,0,cube.columns,scs_c=np.array(model['topographic_c'],np.float32)) if topo else cube.data
  image=mod.apply_brdf_correct(cube,data,0,cube.lines,0,cube.columns,coeff_path=path,brdf_kernel_config=mod.HYTOOLS_BRDF_KERNEL_CONFIG,input_stage='topographic_only' if topo else 'uncorrected');images.append(image.copy());assert np.array_equal(original,cube.data,equal_nan=True)
  if label=='after':
   stem=folder/'serialized';header=cube.build_envi_header();header.update({'brdf status':'INCOMPLETE','brdf model schema':2,'brdf kernel math version':after.BRDF_KERNEL_MATH_VERSION,'brdf validation policy':after.BRDF_VALIDATION_POLICY});writer=EnviWriter(stem,header);writer.write_chunk(image,0,0);writer.close();finalize_scientific_header(stem.with_suffix('.hdr'),header,brdf_status='VALID');assert library_radiometry(stem.with_suffix('.img')).status=='VALID'
   with rasterio.open(stem.with_suffix('.img')) as src:assert np.array_equal(image,np.moveaxis(src.read(),0,-1),equal_nan=True)
 assert np.array_equal(*images,equal_nan=True)
 results.append(dict(topographic=topo,status='VALID',stored_values_exact=images[0].size,source_immutable=True,serialized_exact=True,approved_neon_header=True));print('NEON',topo,'exact',images[0].size,flush=True)
(HERE/'neon_control.json').write_text(json.dumps(dict(source=str(NEON),source_sha256=sha(NEON),window=[350,470,1000,4000],bands=selected.tolist(),results=results),indent=2)+'\n')
