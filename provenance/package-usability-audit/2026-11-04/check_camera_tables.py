"""Read-only inventory/staging of user-supplied camera metadata; no correction."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT='/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023'
GOCMD='/private/tmp/spectralbridge-gocmd/gocmd'
LOCAL=Path('/private/tmp/spectralbridge-usability-20261104/camera_tables')
LOCAL.mkdir(parents=True,exist_ok=True)

def listing(path):
    data=json.loads(subprocess.check_output([GOCMD,'ls','-L','--output_json',path],text=True))
    return [r for group in data for r in group.get('data',[]) if r.get('Name')]


def main():
    result=[]
    for entry in listing(ROOT):
        package=entry['Name']
        if not package.upper().startswith('AOP') or entry['Type']!='collection':continue
        path=ROOT+'/'+package
        matches={r['Name']:r for r in listing(path) if r['Type']=='data-object' and r['Name'].lower().endswith('-camera-locations.csv') and r.get('Status')=='Good'}
        item=dict(package=package,source_directory=path,candidates=list(matches))
        if len(matches)!=1:
            item['status']='MISSING_OR_AMBIGUOUS';result.append(item);continue
        name,metadata=next(iter(matches.items()))
        source=path+'/'+name
        destination=LOCAL/package/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        expected=metadata['Checksum']
        if not destination.exists() or hashlib.md5(destination.read_bytes()).hexdigest()!=expected:
            partial=destination.with_suffix('.csv.part')
            subprocess.run([GOCMD,'get','--verify_checksum',source,str(partial)],check=True,capture_output=True,text=True)
            if hashlib.md5(partial.read_bytes()).hexdigest()!=expected:raise RuntimeError('Checksum mismatch: '+source)
            partial.replace(destination)
        item.update(status='DOWNLOADED_CHECKSUM_VERIFIED_NOT_GEOMETRY_CERTIFIED',remote_path=source,local_path=str(destination),remote_md5=expected,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),size_bytes=destination.stat().st_size)
        result.append(item)
        print(package,name,destination.stat().st_size,'bytes verified; run validate_camera_tables.py for format inspection',flush=True)
    (HERE/'camera_table_inventory.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
