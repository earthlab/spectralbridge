"""Bounded multi-object GoCommands transfer with per-object remote MD5 checks."""
import json,subprocess,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
P=Path(__file__).resolve().parent;R=P.parents[1];SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');STAGE=Path('/private/tmp/p184-transfer-batches');STAGE.mkdir(exist_ok=True)
selected=set(json.loads((P/'photo_selection.json').read_text()));inventory=json.loads((R/'provenance/metashape-recovery/2026-11-05/remote_inventory.json').read_text());rows=[r for r in inventory['objects'] if r['remote_path'] in selected];manifest=P/'retrieval_manifest.json';records={};pending=[];start=time.monotonic()
staged_by_name={}
for staged in STAGE.glob('*/*.tif'):staged_by_name.setdefault(staged.name,[]).append(staged)
def digest(path,method):
 h=hashlib.new(method)
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
def verified(r,path):return path.exists() and path.stat().st_size==r['bytes'] and digest(path,'md5')==r['checksum']
def record(r,path):return dict(**r,local_path=str(path),sha256=digest(path,'sha256'),remote_md5_verified=True)
for r in rows:
 path=SRC/r['relative_path']
 if not verified(r,path):
  for staged in staged_by_name.get(path.name,[]):
   if verified(r,staged):path.parent.mkdir(parents=True,exist_ok=True);staged.replace(path);break
 if verified(r,path):records[r['remote_path']]=record(r,path)
 else:pending.append(r)
manifest.write_text(json.dumps(list(records.values()),indent=2)+'\n');print('Verified reusable',len(records),'pending',len(pending),flush=True)
# Batches retain distinct basenames; group by source directory to prevent collisions.
groups={}
for r in pending:groups.setdefault(str(Path(r['relative_path']).parent),[]).append(r)
batches=[rr[i:i+80] for rr in groups.values() for i in range(0,len(rr),80)]
def transfer(index,batch):
 stage=STAGE/str(index);stage.mkdir(exist_ok=True)
 for attempt in range(4):
  need=[r for r in batch if not verified(r,stage/Path(r['relative_path']).name)]
  if not need:break
  cmd=['/private/tmp/spectralbridge-gocmd/gocmd','get','--verify_checksum','--yes','--thread_num','3','--thread_num_per_file','1',*[r['remote_path'] for r in need],str(stage)]
  proc=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
  if proc.returncode and attempt<3:time.sleep(min(30,5*2**attempt))
  if proc.returncode and attempt==3:raise RuntimeError(proc.stderr[-1000:])
 result=[]
 for r in batch:
  staged=stage/Path(r['relative_path']).name
  if not verified(r,staged):raise ValueError('Checksum mismatch: '+r['remote_path'])
  target=SRC/r['relative_path'];target.parent.mkdir(parents=True,exist_ok=True);staged.replace(target);result.append(record(r,target))
 return result
with ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(transfer,i,b) for i,b in enumerate(batches)]
 for f in as_completed(futures):
  for r in f.result():records[r['remote_path']]=r
  manifest.write_text(json.dumps(list(records.values()),indent=2)+'\n');print('Verified',len(records),'/',len(rows),'elapsed_s',round(time.monotonic()-start),flush=True)
print('Complete',sum(r['bytes'] for r in records.values()),flush=True)
