"""Bounded reconstruction with the existing nadir/center-weighted kernel scenario."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time
from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer,Geod
from spectralbridge import corrections as c
from spectralbridge.drone_view_geometry import NadirFootprint,camera_rays,footprint_candidates,assign_camera,aggregate_kernels
from prepare_rerun import HERE,ROOT,WORK,sha,write
FIELDS=['candidate_count','central_zenith_deg','central_azimuth_deg','nearest_zenith_deg','nearest_azimuth_deg','center_RossThick','center_LiDenseR']

def reconstruct(config):
    site=config['site'];folder=WORK/site.lower();folder.mkdir(parents=True,exist_ok=True)
    signature=hashlib.sha256(json.dumps(dict(inputs=config['input_sha256'],implementation=config['implementation_sha256'],script=sha(__file__),policy='P173 nadir C-center',block=1024),sort_keys=True).encode()).hexdigest()
    marker=folder/'geometry_complete.json'
    if marker.exists():
        previous=json.loads(marker.read_text())
        if previous['signature']!=signature:raise ValueError('Stale geometry stage; preserve and choose a new namespace: '+site)
        if all(sha(p)==h for p,h in previous['output_sha256'].items()):
            print(site,'geometry reused after checksum verification',flush=True);return
        raise ValueError('Geometry output corruption detected: '+site)
    with rasterio.open(config['prepared']) as src:
        mask=src.dataset_mask()>0;shape=src.shape;transform=src.transform;profile=src.profile.copy();bounds=src.bounds
    with rasterio.open(config['terrain']) as src:
        terrain=src.read(1);terrain=np.where(src.read_masks(1)>0,terrain,np.nan)
    positions=pd.read_csv(config['camera_positions']);cameras=positions[['X','Y','Z']].to_numpy();heading=positions.heading_grid_rad.to_numpy()
    solar=np.load(config['solar_arrays'],mmap_mode='r')
    solar_zen=solar[...,0];solar_az=solar[...,1]
    eligible=mask&np.isfinite(terrain)&np.isfinite(solar_az)&np.isfinite(solar_zen)
    scene=float(np.mean(np.deg2rad(solar_zen[eligible].astype(np.float32)),dtype=np.float64))
    ll=Transformer.from_crs(config['crs'],4326,always_xy=True);geod=Geod(ellps='GRS80')
    center=((bounds.left+bounds.right)/2,(bounds.bottom+bounds.top)/2)
    rotation=geod.inv(*ll.transform(*center),*ll.transform(center[0],center[1]+10))[0]
    intrinsic=config['intrinsics'];footprint=NadirFootprint(**{k:intrinsic[k] for k in ['width_px','height_px','focal_mm','pixel_um']})
    maps=np.lib.format.open_memmap(folder/'geometry.npy',mode='w+',dtype='float32',shape=(*shape,len(FIELDS)));maps[:]=np.nan
    design=np.lib.format.open_memmap(folder/'center_design.npy',mode='w+',dtype='float64',shape=(*shape,3));design[:]=np.nan
    indices=np.flatnonzero(eligible);width=shape[1];total=(len(indices)+1023)//1024
    def block(ids):
        row,col=ids//width,ids%width
        ground=np.stack([transform.c+(col+.5)*transform.a,transform.f+(row+.5)*transform.e,terrain[row,col]],axis=-1)
        zen,az,delta=camera_rays(ground,cameras,grid_to_true_deg=rotation)
        good,central=footprint_candidates(delta,heading,footprint)
        ii,jj=np.nonzero(good);sun=np.deg2rad(solar_az[row,col].astype(np.float32))
        z32=np.deg2rad(np.rad2deg(zen[ii,jj]).astype(np.float32));a32=np.deg2rad(np.rad2deg(az[ii,jj]).astype(np.float32))
        volume=np.full(good.shape,np.nan);geom=volume.copy()
        volume[ii,jj]=c.calc_volume_kernel(sun[ii],np.float32(scene),a32,z32,'RossThick')
        geom[ii,jj]=c.calc_geom_kernel(sun[ii],np.float32(scene),a32,z32,'LiDenseR',b_r=10,h_b=2)
        blended=aggregate_kernels(volume,geom,good,centrality=central)
        values=np.full((len(ids),len(FIELDS)),np.nan,np.float32);values[:,0]=good.sum(1)
        for rule,offset in [('central',1),('nearest',3)]:
            assigned=assign_camera(delta,good,central,rule=rule);support=assigned>=0;k=np.flatnonzero(support);j=assigned[support]
            values[k,offset]=np.rad2deg(zen[k,j]);values[k,offset+1]=np.rad2deg(az[k,j])
        values[:,5:7]=blended[:,1:]
        return ids,values,blended
    start=time.monotonic();chunks=(indices[i:i+1024] for i in range(0,len(indices),1024))
    print(site,'reconstructing',len(indices),'ground cells with',len(cameras),'positions;',total,'bounded chunks',flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending=deque()
        for _ in range(6):
            chunk=next(chunks,None)
            if chunk is not None:pending.append(pool.submit(block,chunk))
        completed=0
        while pending:
            ids,values,kernels=pending.popleft().result();maps.reshape(-1,len(FIELDS))[ids]=values;design.reshape(-1,3)[ids]=kernels
            completed+=1
            if completed%200==0 or completed==total:print(site,'geometry',completed,'/',total,'elapsed_s',round(time.monotonic()-start),flush=True)
            chunk=next(chunks,None)
            if chunk is not None:pending.append(pool.submit(block,chunk))
    maps.flush();design.flush()
    profile.update(count=len(FIELDS),dtype='float32',nodata=np.nan,compress='deflate',predictor=3,tiled=True,blockxsize=256,blockysize=256)
    profile.pop('photometric',None)
    output=folder/'experimental_view_geometry.tif';partial=folder/'experimental_view_geometry.part.tif'
    with rasterio.open(partial,'w',**profile) as dst:
        for band,name in enumerate(FIELDS,1):dst.write(maps[...,band-1],band);dst.set_band_description(band,name)
        dst.update_tags(SCIENTIFIC_STATUS='EXPERIMENTAL_UNVERIFIED_CONTRIBUTORS',ORIENTATION='nadir optical-axis and flight-heading footprint assumptions',CRS_INTERPRETATION=config['camera_metadata']['adopted_crs'])
    partial.replace(output)
    count=maps[...,0];covered=mask&np.isfinite(count)&(count>0)
    record=dict(signature=signature,site=site,scientific_status='EXPERIMENTAL',source_footprint_pixels=int(mask.sum()),geometry_eligible_pixels=len(indices),covered_pixels=int(covered.sum()),unsupported_source_pixels=int((mask&~covered).sum()),candidate_count_quantiles=np.quantile(count[covered],[0,.25,.5,.75,1]).tolist(),grid_to_true_north_rotation_deg=rotation,scene_solar_zenith_deg=float(np.rad2deg(scene)),central_zenith_quantiles=np.quantile(maps[...,1][covered],[0,.25,.5,.75,1]).tolist(),elapsed_seconds=time.monotonic()-start,memory_contract='1024 ground cells x all cameras; at most6 futures/3 workers; memmapped design/maps; one observation per ground cell, not duplicated by camera',output_sha256={str(p):sha(p) for p in [output,folder/'geometry.npy',folder/'center_design.npy']})
    write(marker,record);write(HERE/(site.lower()+'_geometry.json'),record)
    print(site,'geometry complete:',record['covered_pixels'],'covered',flush=True)

def main():
    for config in json.loads((HERE/'site_inputs.json').read_text()):reconstruct(config)
if __name__=='__main__':main()
