"""Freeze three-site inputs and join camera poses to existing photo timestamps."""
import hashlib,json,subprocess
from datetime import timezone
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from spectralbridge.drone_view_geometry import read_metashape_camera_locations
from spectralbridge.pipelines.drone import _validate_drone_tiff_ancillary_alignment, _compute_solar_geometry_arrays
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORK=ROOT/'archive/local/drone-camera-rerun/2026-11-05/photo_clock_v1'
OLD=ROOT/'archive/local/drone-three-site-integration/2026-11-04'
REMOTE=json.loads((HERE/'current_remote_inputs.json').read_text())
POLYGONS=ROOT/'Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2,default=str,allow_nan=False)+'\n');temp.replace(path)

def main():
    manifests=[]
    preservation=json.loads((ROOT/'provenance/photogrammetry-metadata/2026-11-02/preservation.json').read_text())
    for site in ['Gordon','Goldhill','Ruby']:
        old=next(json.loads(p.read_text()) for p in (OLD/'outputs').glob('*/source_manifest.json') if site.lower() in p.parent.name.lower())
        source=Path(old['original_local']['path']);prepared=Path(old['prepared']['output'])
        assert sha(source)==old['original_local']['sha256']
        assert sha(prepared)==old['prepared']['output_sha256']
        sources=[r for r in REMOTE if r['site']==site]
        camera=next(Path(r['local_path']) for r in sources if r['local_path'].endswith('.csv'))
        kwargs={}
        if site=='Goldhill':kwargs=dict(crs_override=26913,crs_override_provenance='Processing report project and DEM EPSG:26913 (report pages18/19); independently documented in provenance/goldhill-viewing-geometry/2026-11-04/flight_and_crs.json; current XY/raster overlap. Source says5070 and remains unchanged.')
        photos,meta=read_metashape_camera_locations(camera,**kwargs)
        metadata_files=sorted(source.parent.rglob('SD*_image_metadata.csv'))
        frames=[]
        for file in metadata_files:
            frame=pd.read_csv(file);frame['source_metadata_file']=str(file);frames.append(frame)
        tags=pd.concat(frames,ignore_index=True)
        tags['PhotoID']=tags.filename.map(lambda s:Path(s).stem)
        tags['timestamp_unzoned']=pd.to_datetime(tags.TIFFTAG_DATETIME,format='%Y:%m:%d %H:%M:%S',errors='raise')
        if not tags.PhotoID.is_unique:raise ValueError('Ambiguous photo bindings: '+site)
        merged=photos.merge(tags,on='PhotoID',how='left',validate='one_to_one')
        if merged.timestamp_unzoned.isna().any():raise ValueError('Camera IDs do not uniquely match photo timestamps: '+site)
        positions=merged.sort_values(['timestamp_unzoned','PhotoID']).drop_duplicates(['X','Y','Z']).reset_index(drop=True)
        xyz=positions[['X','Y','Z']].to_numpy();delta=np.gradient(xyz[:,:2],axis=0)
        positions['heading_grid_rad']=np.arctan2(delta[:,0],delta[:,1])
        positions['order']=np.arange(len(positions))
        folder=WORK/site.lower();folder.mkdir(parents=True,exist_ok=True)
        poses=folder/'camera_poses_with_photo_times.csv';merged.to_csv(poses,index=False)
        position_path=folder/'camera_positions.csv';positions.to_csv(position_path,index=False)
        terrain=Path('/private/tmp/photogrammetry-metadata-20261102')/(site.lower()+'_aligned_dem.tif')
        assert sha(terrain)==preservation['inputs_before'][str(terrain)]
        with rasterio.open(prepared) as raster:
            shape=raster.shape
            assert raster.crs.to_string()==meta['adopted_crs']
            aligned={}
            for kind in ['slope','aspect']:
                path=next(Path(r['local_path']) for r in sources if Path(r['local_path']).name=='aligned_'+kind+'.tif')
                data=_validate_drone_tiff_ancillary_alignment(prepared,shape,raster.transform,raster.crs.to_wkt(),path)
                with rasterio.open(path) as anc:
                    valid=(anc.read_masks(1)>0)&np.isfinite(data)
                if not valid.any():raise ValueError('No terrain observations: '+site)
                if kind=='slope' and (data[valid].min()<0 or data[valid].max()>90):raise ValueError('Slope units not degrees')
                if kind=='aspect' and (data[valid].min()<0 or data[valid].max()>360):raise ValueError('Aspect units not degrees')
                aligned[kind]=str(path)
            _validate_drone_tiff_ancillary_alignment(prepared,shape,raster.transform,raster.crs.to_wkt(),terrain)
            r,c=rasterio.transform.rowcol(raster.transform,xyz[:,0],xyz[:,1]);r=np.asarray(r);c=np.asarray(c)
            inside=(r>=0)&(r<shape[0])&(c>=0)&(c<shape[1])
            with rasterio.open(terrain) as dem:
                heights=np.array([p[0] for p in dem.sample(xyz[:,:2],masked=True)],dtype=float)
                heights[~np.isfinite(heights) | (heights<-1000)]=np.nan
            agl=xyz[:,2]-heights
            valid_agl=np.isfinite(agl)&(agl>0)&inside
            midpoint=merged.timestamp_unzoned.min()+(merged.timestamp_unzoned.max()-merged.timestamp_unzoned.min())/2
            solar_path=folder/'photo_midpoint_solar.npy'
            solar=np.lib.format.open_memmap(solar_path,mode='w+',dtype='float32',shape=(*shape,2))
            to_lonlat=Transformer.from_crs(raster.crs,4326,always_xy=True)
            for row in range(0,shape[0],128):
                end=min(row+128,shape[0]);rr,cc=np.mgrid[row:end,:shape[1]]
                x=raster.transform.c+(cc+.5)*raster.transform.a;y=raster.transform.f+(rr+.5)*raster.transform.e
                lon,lat=to_lonlat.transform(x,y)
                zen,az=_compute_solar_geometry_arrays(acquisition_datetime=midpoint.to_pydatetime().replace(tzinfo=timezone.utc),longitude=lon,latitude=lat)
                solar[row:end,:,0]=zen;solar[row:end,:,1]=az
            solar.flush()
            record=dict(site=site,flight_stem=old['flight_stem'],source=str(source),prepared=str(prepared),terrain=str(terrain),
                terrain_ancillary=aligned,camera=str(camera),camera_metadata=meta,camera_poses=str(poses),camera_positions=str(position_path),
                camera_position_count=len(positions),positions_inside_processing_bounds=int(inside.sum()),positions_with_positive_height_inside=int(valid_agl.sum()),
                camera_height_above_surface_min_max=[float(agl[valid_agl].min()),float(agl[valid_agl].max())],
                shape=list(shape),transform=list(raster.transform),crs=raster.crs.to_string(),
                photo_clock_start=str(merged.timestamp_unzoned.min()),photo_clock_end=str(merged.timestamp_unzoned.max()),
                timestamp_join='All camera IDs uniquely matched to original SD1/SD2 photo metadata. Clock zone remains unverified; UTC is an explicit scenario, not independent clock certification.',solar_arrays=str(solar_path),solar_datetime=str(midpoint),solar_policy='Existing NOAA helper at matched-photo midpoint, explicit unverified UTC interpretation; Ruby manifest date16Aug not adopted because matched photo tags show15Aug',
                original_package_clipped=old['clipped_export'],wavelengths_nm=old['wavelengths_nm'],
                preparation_radiometry='Original DN*10000/65535, zero offset; no min/max adjustment; physical calibration UNVERIFIED',
                experimental_physical_interpretation='Same prior P172/P175 DN/32768 hypothesis; stored10K multiplier65535/(10000*32768); never production VALID',
                intrinsics=dict(width_px=1280,height_px=960,focal_mm=5.5,pixel_um=3.75,source='This site processing report Table1 pages2-3; undistorted nadir footprint assumption'),
                pose_convention='Rotation matrices retained/checked but convention unverified; established nadir/flight-heading scenario, not recovered contributors',
                solar_h5=str(next((OLD/'outputs'/old['flight_stem']/'preparation_pipeline').rglob('*__working.h5'))),
                polygon_index=str(next((OLD/'outputs'/old['flight_stem']/'preparation_pipeline').rglob('*__polygon_index.parquet'))),
                polygons=str(POLYGONS),polygon_definition='Established half-diameter researcher polygons; exclude evaluation pixels plus20-step Manhattan buffer from fitting',
                software_version=__import__('spectralbridge').__version__,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                correction_policy='Existing conditioned SCS+C policy, source-only training and20m uncertainty clusters; C-center simulated individual-ray kernels; no fit-cap or coefficient tuning')
        required=[source,prepared,terrain,camera,poses,position_path,POLYGONS,*map(Path,aligned.values()),*metadata_files,Path(record['solar_h5']),solar_path]
        record['input_sha256']={str(p):sha(p) for p in required}
        record['implementation_sha256']={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/spectralbridge/drone_view_geometry.py',ROOT/'src/spectralbridge/corrections.py',ROOT/'src/spectralbridge/topographic.py',ROOT/'src/spectralbridge/pipelines/drone.py']}
        write(HERE/(site.lower()+'_inputs.json'),record);write(folder/'source_manifest.json',record);manifests.append(record)
        print(site,shape,len(positions),'positions; exact grids; unique camera timestamp joins',flush=True)
    write(HERE/'site_inputs.json',manifests)
if __name__=='__main__':main()
