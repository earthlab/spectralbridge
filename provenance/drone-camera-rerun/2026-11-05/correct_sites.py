"""Existing shared correction driver under the prior isolated experimental boundary."""
import argparse,hashlib,importlib.util,json,logging,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import binary_dilation
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.envi import hdr_to_dict
from spectralbridge.neon_cube import NeonCube
from spectralbridge.radiometry import require_library_header
from prepare_rerun import HERE,ROOT,WORK,sha,write
support_path=ROOT/'provenance/drone-integrated-reliability/2026-11-04/experiment_support.py'
spec=importlib.util.spec_from_file_location('p181_prior_isolated_support',support_path)
support=importlib.util.module_from_spec(spec);sys.modules[spec.name]=support;spec.loader.exec_module(support)
SCALE=65535/(10000*32768)


def clean(value):return support.safe(value)


def load_cube(config):
    folder=WORK/config['site'].lower();shape=tuple(config['shape'])
    with rasterio.open(config['prepared']) as src:
        footprint=src.dataset_mask()>0;profile=src.profile.copy();transform=src.transform;crs=src.crs
        raw_path=folder/'candidate_stored.npy'
        if not raw_path.exists():
            array=np.lib.format.open_memmap(raw_path,mode='w+',dtype='float32',shape=(*shape,10))
            for y in range(0,shape[0],128):
                block=src.read(window=rasterio.windows.Window(0,y,shape[1],min(128,shape[0]-y)))
                array[y:y+block.shape[1]]=np.moveaxis(block,0,-1)
            array.flush()
        raw=np.load(raw_path,mmap_mode='r')
    maps=np.load(folder/'geometry.npy',mmap_mode='r');design=np.load(folder/'center_design.npy',mmap_mode='r')
    with rasterio.open(config['terrain']) as src:terrain_good=(src.read_masks(1)>0)&np.isfinite(src.read(1))
    reference=NeonCube(config['solar_h5']);header=support.drone._drone_envi_header(reference)
    solar=np.load(config['solar_arrays'],mmap_mode='r')
    geometry=dict(solar_zn=np.asarray(solar[...,0]),solar_az=np.asarray(solar[...,1]))
    for name,path in config['terrain_ancillary'].items():
        with rasterio.open(path) as src:
            a=src.read(1);geometry[name]=np.where(src.read_masks(1)>0,a,np.nan)
    geometry.update(sensor_zn=np.asarray(maps[...,1]),sensor_az=np.asarray(maps[...,2]))
    cube=support.Cube(raw,footprint&terrain_good&(maps[...,0]>0),geometry,scale=SCALE,footprint=footprint)
    cube.h5_path=Path(config['prepared']);cube.projection_wkt=crs.to_wkt();cube.transform=transform.to_gdal()
    cube.chunk_count=lambda chunk_y=128,chunk_x=None:int(np.ceil(cube.lines/chunk_y))
    header.update(cube.radiometry.header());header.update({'reflectance scale factor':1/SCALE,'data ignore value':np.nan,'scientific validation status':'EXPERIMENTAL','solar geometry source':'Matched photo midpoint; explicit unverified UTC scenario','acquisition datetime used':config['solar_datetime'],'description':'P181 conditional DN/32768 candidate; stored=sourceDN*10000/65535; physical calibration unverified'})
    cube.build_envi_header=lambda:dict(header)
    return cube,design,maps,profile


def site(config):
    name=config['site'];folder=WORK/name.lower()
    geom=json.loads((folder/'geometry_complete.json').read_text())
    signature=hashlib.sha256(json.dumps(dict(inputs=config['input_sha256'],implementation=config['implementation_sha256'],geometry=geom['signature'],driver=sha(__file__),adapter=sha(support_path),policy='P175 unchanged conditioned SCSC; center simulated kernels;20mclusters;2mpolygonbuffer'),sort_keys=True).encode()).hexdigest()
    checkpoint=folder/'corrections_complete.json'
    if checkpoint.exists():
        record=json.loads(checkpoint.read_text())
        if record['signature']!=signature:raise ValueError('Stale correction checkpoint: '+name)
        if all(sha(p)==h for p,h in record['output_sha256'].items()):print(name,'all correction products reused after hash checks',flush=True);return
        raise ValueError('Changed correction artifact: '+name)
    cube,design,maps,profile=load_cube(config)
    # Verify that the experiment never changes normal production calibration acceptance.
    try:cube.radiometry.require_valid()
    except ValueError:pass
    else:raise AssertionError('Experimental radiometry must remain unapproved')
    before=support.c.require_radiometry;shape=cube.data.shape[:2]
    rr,cc=np.indices(shape);groups=((rr//200)*((shape[1]+199)//200)+cc//200).astype('int32')
    index=pd.read_parquet(config['polygon_index']);evaluation=np.zeros(shape,bool);evaluation[index.row,index.col]=True
    training=cube.mask_no_data&~binary_dilation(evaluation,iterations=20)
    np.save(folder/'training_mask.npy',training);np.save(folder/'spatial_groups.npy',groups)
    print(name,'conditioned SCS+C fit;',int(training.sum()),'training pixels',flush=True)
    model=support.isolated(support.topo.fit_conditioned_scs_c)(cube,policy=support.topo.SCSCPolicy(),uncertainty_groups=groups,fitting_mask=training,provenance={'site':name,'source_manifest':str(folder/'source_manifest.json'),'fit_mask':'Researcher half-diameter polygons plus20-step Manhattan buffer excluded','clusters':'20m x20m source-grid blocks; not independent physical replications','calibration':'Conditional unverified DN/32768','geometry':'P173 nadir C-center simulated weights; contributor/datum conventions unverified'})
    write(folder/'conditioned_scsc_model.json',clean(model));write(HERE/(name.lower()+'_conditioned_scsc_model.json'),clean(model))
    print(name,'SCS+C model',model['validation_status'],[(r['band'],r['status']) for r in model['fits']],flush=True)
    rawstem=folder/(config['flight_stem']+'__experimental_candidate')
    writer=EnviWriter(rawstem,cube.build_envi_header())
    for y in range(0,cube.lines,128):writer.write_chunk(np.asarray(cube.data[y:y+128]),y,0)
    writer.close()
    design_hash=sha(folder/'center_design.npy')
    records=[];artifacts=[rawstem.with_suffix('.img'),rawstem.with_suffix('.hdr'),folder/'conditioned_scsc_model.json',folder/'training_mask.npy',folder/'spatial_groups.npy']
    for branch,topographic,brdf in [('topographic_only',True,False),('brdf_only',False,True),('combined',True,True)]:
        started=time.monotonic();branch_dir=folder/branch;branch_dir.mkdir(exist_ok=True)
        stem=branch_dir/(config['flight_stem']+'__'+branch+'_EXPERIMENTAL')
        print(name,'actual shared drone correction driver:',branch,flush=True)
        try:
            image,header,audit=support.isolated(support.drone.apply_drone_corrections,design,design_hash)(cube=cube,envi_img=rawstem.with_suffix('.img'),envi_hdr=rawstem.with_suffix('.hdr'),corrected_stem=stem,apply_topo=topographic,apply_brdf=brdf,topographic_model=model if topographic else None,brdf_fitting_mask=training if brdf else None,brdf_fitting_provenance={'strategy':'Exclude evaluation polygons and2mManhattanbuffer','source_camera_sha256':config['camera_metadata']['source_sha256'],'geometry':'Center-weighted candidate ray kernels, not recovered contributors','calibration':'HYPOTHETICAL_UNVERIFIED DN/32768','uncertainty':'20m spatial clusters'} if brdf else None,brdf_uncertainty_groups=groups if brdf else None)
            record=dict(site=name,branch=branch,status='EXECUTED_EXPERIMENTAL',audit=clean(audit),image=str(image),header=str(header),elapsed_seconds=time.monotonic()-started)
            expected=hdr_to_dict(header)
            assert expected['radiometry status']=='HYPOTHETICAL_UNVERIFIED'
            assert expected['scientific validation status']=='EXPERIMENTAL'
            try:require_library_header(expected)
            except ValueError:pass
            else:raise AssertionError('Experimental outputs cannot enter approved libraries')
            native=branch_dir/(stem.name+'.tif');temp=native.with_suffix('.part.tif')
            p=dict(profile,count=10,dtype='float32',nodata=np.nan,compress='deflate',predictor=3,tiled=True,blockxsize=256,blockysize=256);p.pop('photometric',None)
            with rasterio.open(image) as src,rasterio.open(temp,'w',**p) as dst:
                for b in range(1,11):dst.write(src.read(b),b);dst.set_band_description(b,str(cube.wavelengths[b-1])+' nm')
                dst.update_tags(SCIENTIFIC_STATUS='EXPERIMENTAL_NOT_PRODUCTION_APPROVED',PHYSICAL_CALIBRATION_STATUS='HYPOTHETICAL_UNVERIFIED',HYPOTHETICAL_PHYSICAL_MULTIPLIER=str(SCALE),STORED_UNITS='originalDN*10000/65535; no min/max adjustment or clipping',CAMERA_CONTRIBUTORS='UNVERIFIED',SOURCE_MANIFEST=str(folder/'source_manifest.json'),TOPO_REQUESTED=str(topographic),BRDF_REQUESTED=str(brdf))
            temp.replace(native);record['geotiff']=str(native);artifacts.extend([image,header,native])
        except support.drone.DroneCorrectionUnavailableError as exc:
            record=dict(site=name,branch=branch,status='UNSUPPORTED',reason=str(exc),audit=clean(exc.audit),elapsed_seconds=time.monotonic()-started)
        records.append(record)
        models=list(branch_dir.glob('*brdf_model.json'))
        for path in models:
            artifacts.append(path);write(HERE/(name.lower()+'_'+branch+'_brdf_model.json'),json.loads(path.read_text()))
        write(folder/'pipeline_results.json',clean(records));write(HERE/(name.lower()+'_pipeline_results.json'),clean(records))
        print(name,branch,record['status'],record.get('reason',''),flush=True)
    status_path=folder/'topographic_status.tif';p=dict(profile,count=10,dtype='uint8',nodata=None,compress='deflate',predictor=1,tiled=True,blockxsize=256,blockysize=256);p.pop('photometric',None)
    with rasterio.open(status_path,'w',**p) as out:
        for y in range(0,cube.lines,128):
            end=min(y+128,cube.lines);result=support.isolated(support.topo.apply_conditioned_scs_c)(cube,np.asarray(cube.data[y:end]),y,end,0,cube.columns,model=model)
            out.write(np.moveaxis(result.status,2,0),window=rasterio.windows.Window(0,y,cube.columns,end-y))
        out.update_tags(STATUS_CODES='0 missing/invalid;1 unsupported illumination/model;2 corrected',SCIENTIFIC_STATUS='EXPERIMENTAL')
    artifacts.append(status_path)
    assert support.c.require_radiometry is before
    result=dict(site=name,signature=signature,scientific_status='EXPERIMENTAL_NOT_PRODUCTION_APPROVED',branches=clean(records),production_gate_preserved=True,output_sha256={str(p):sha(p) for p in artifacts})
    write(checkpoint,result);write(HERE/(name.lower()+'_correction_summary.json'),result)
    print(name,'correction stage complete',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site');args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    configs=json.loads((HERE/'site_inputs.json').read_text())
    for config in configs:
        if args.site is None or config['site'].lower()==args.site.lower():site(config)
if __name__=='__main__':main()
