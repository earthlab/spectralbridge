"""Refresh small camera/terrain inputs only; original spectral imagery stays local."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
WORK=ROOT/'archive/local/drone-camera-rerun/2026-11-05'
REMOTE='/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023'
GOCMD='/private/tmp/spectralbridge-gocmd/gocmd'
old=json.loads((ROOT/'provenance/package-usability-audit/2026-11-04/camera_table_inventory.json').read_text())
rows=[]
for site in ['Gordon','Goldhill','Ruby']:
    entry=next(r for r in old if site.lower() in r['package'].lower())
    for role,root in [('camera',REMOTE),('terrain',REMOTE+'-10cm-10k')]:
        directory=root+'/'+entry['package']
        groups=json.loads(subprocess.check_output([GOCMD,'ls','-L','--output_json',directory],text=True))
        children={r['Name']:r for group in groups for r in group.get('data',[]) if r.get('Name') and r.get('Type')=='data-object' and r.get('Status')=='Good'}
        selected=[r for name,r in children.items() if (role=='camera' and name.lower().endswith('-camera-locations.csv')) or (role=='terrain' and name.lower() in {'aligned_slope.tif','aligned_aspect.tif'})]
        print(site,role,'selected',[(r['Name'],r['Size']) for r in selected],flush=True)
        for remote in selected:
            local=WORK/'inputs'/role/entry['package']/remote['Name'];local.parent.mkdir(parents=True,exist_ok=True)
            expected=remote['Checksum']
            if len(expected)!=32:raise ValueError('Expected remote MD5, received '+expected)
            md5=lambda p:hashlib.md5(p.read_bytes()).hexdigest()
            reused=local.exists() and md5(local)==expected
            if not reused:
                partial=local.with_suffix(local.suffix+'.part')
                if partial.exists():partial.unlink()
                subprocess.run([GOCMD,'get','--verify_checksum',directory+'/'+remote['Name'],str(partial)],check=True,capture_output=True,text=True)
                assert md5(partial)==expected
                partial.replace(local)
            rows.append(dict(site=site,role=role,remote_path=directory+'/'+remote['Name'],local_path=str(local),size_bytes=local.stat().st_size,remote_md5=expected,sha256=hashlib.sha256(local.read_bytes()).hexdigest(),checksum_verified=True,status='reused' if reused else 'downloaded'))
            print(site,local.name,'verified',flush=True)
(HERE/'current_remote_inputs.json').write_text(json.dumps(rows,indent=2)+'\n')
