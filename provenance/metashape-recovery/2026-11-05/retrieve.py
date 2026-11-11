"""Checksum-verified staged retrieval preserving exact remote-relative paths."""
import json,subprocess,hashlib,argparse,time,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];DEST=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';GOCMD='/private/tmp/spectralbridge-gocmd/gocmd'
p=argparse.ArgumentParser();p.add_argument('--stage',choices=['metadata','project','selected'],default='metadata');p.add_argument('--selection');p.add_argument('--destination-root',type=Path);args=p.parse_args();LEGACY=DEST;DEST=args.destination_root.resolve() if args.destination_root else DEST;inventory=json.loads((HERE/'remote_inventory.json').read_text());objects=inventory['objects']
if args.stage=='metadata':
 selected=[r for r in objects if Path(r['relative_path']).suffix.lower() in ['.psx','.xml','.json','.txt','.csv','.log','.pdf'] and r['bytes']<20_000_000 or Path(r['relative_path']).name in ['project.zip','chunk.zip','frame.zip']]
elif args.stage=='project':selected=[r for r in objects if '.files/' in r['relative_path'] or r['relative_path'].endswith('.psx')]
else:
 paths=set(json.loads(Path(args.selection).read_text()));selected=[r for r in objects if r['remote_path'] in paths];assert len(selected)==len(paths)
print('Retrieval stage',args.stage,'files',len(selected),'GB',sum(r['bytes'] for r in selected)/1e9,flush=True);started=time.monotonic()
def digest(path,method='sha256'):
 h=hashlib.new(method)
 with path.open('rb') as f:
  for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
 return h.hexdigest()
def get(r):
 path=DEST/r['relative_path'];path.parent.mkdir(parents=True,exist_ok=True);expected=r['checksum'];assert len(expected)==32,'Require remote MD5 for this retrieval'
 reused=path.exists() and path.stat().st_size==r['bytes'] and digest(path,'md5')==expected
 copied=False
 if not reused and DEST!=LEGACY:
  source=LEGACY/r['relative_path'];part=path.with_name(path.name+'.part')
  if source.exists():
   try:
    shutil.copyfile(source,part)
    if part.stat().st_size==r['bytes'] and digest(part,'md5')==expected:part.replace(path);reused=True;copied=True
   except OSError:
    # Cloud placeholders can time out; only this fresh temporary copy is retried remotely.
    if part.exists():part.unlink()

 if not reused:
  partial=path.with_name(path.name+'.part')
  for attempt in range(4):
   proc=subprocess.run([GOCMD,'get','--verify_checksum','--yes',r['remote_path'],str(partial)],capture_output=True,text=True,timeout=900)
   if proc.returncode==0:break
   if attempt==3:raise RuntimeError(proc.stderr[-1200:])
   time.sleep(2**attempt)
  if partial.stat().st_size!=r['bytes'] or digest(partial,'md5')!=expected:raise ValueError('Transfer mismatch: '+r['remote_path'])
  partial.replace(path)
 return dict(**r,local_path=str(path),sha256=digest(path),remote_md5_verified=True,reused=reused,copied_from_verified_legacy=copied)
manifest_path=HERE/'retrieval_manifest.json';previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else [];records={r['remote_path']:r for r in previous}
with ThreadPoolExecutor(max_workers=3) as pool:
 for n,r in enumerate(pool.map(get,selected),1):
  old=records.get(r['remote_path'])
  if old and old.get('local_path')!=r['local_path']:r['previous_local_paths']=sorted(set(old.get('previous_local_paths',[])+[old['local_path']]))
  records[r['remote_path']]=r
  if n%10==0 or n==len(selected):print('Verified',n,'/',len(selected),'elapsed_s',round(time.monotonic()-started),flush=True)
  manifest_path.write_text(json.dumps(list(records.values()),indent=2)+'\n')
