"""Read-only, restartable GoCommands inventory; never downloads image pixels."""
import json,subprocess,hashlib,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE='/iplant/home/shared/earthlab/Drone_Calibrations';GOCMD='/private/tmp/spectralbridge-gocmd/gocmd';CACHE=ROOT/'archive/local/metashape-recovery/2026-11-05/listings';CACHE.mkdir(parents=True,exist_ok=True)
start=time.monotonic();objects={};collections=[];todo=[BASE];errors=[]
def list_directory(path):
 cache=CACHE/(hashlib.sha256(path.encode()).hexdigest()+'.json')
 if cache.exists():result=json.loads(cache.read_text())
 else:
  proc=subprocess.run([GOCMD,'ls','-L','--output_json',path],capture_output=True,text=True,timeout=120)
  if proc.returncode:raise RuntimeError(path+': '+proc.stderr[:500])
  result=json.loads(proc.stdout);cache.write_text(json.dumps(result))
 return path,result
with ThreadPoolExecutor(max_workers=4) as pool:
 while todo:
  batch=todo;todo=[]
  if len(collections)+len(batch)>5000:raise ValueError('Inventory exceeds explicit 5000 collection budget')
  for path,result in pool.map(list_directory,batch):
   collections.append(path)
   for group in result:
    if not group['title'].startswith('Content of '):continue
    for r in group['data']:
     if not r.get('Name'):continue
     full=path+'/'+r['Name']
     if r['Type']=='collection':todo.append(full)
     elif r['Status']=='Good':
      rec=dict(remote_path=full,relative_path=full[len(BASE)+1:],bytes=int(r['Size']),checksum=r.get('Checksum',''),modified=r.get('Modify Time',''),replica=int(r['Replica No.']))
      if full not in objects or rec['replica']<objects[full]['replica']:objects[full]=rec
   print('Inventory',len(collections),'collections',len(objects),'objects',round(sum(r['bytes'] for r in objects.values())/1e9,3),'GB; next',len(todo),'elapsed',round(time.monotonic()-start),flush=True)
   (HERE/'remote_inventory.json').write_text(json.dumps(dict(remote_root=BASE,collections=collections,objects=list(objects.values()),status='IN_PROGRESS',errors=errors),indent=2)+'\n')
record=dict(remote_root=BASE,collections=collections,objects=list(objects.values()),status='COMPLETE',errors=errors,unique_objects=len(objects),total_bytes=sum(r['bytes'] for r in objects.values()),elapsed_seconds=time.monotonic()-start)
(HERE/'remote_inventory.json').write_text(json.dumps(record,indent=2)+'\n');print('COMPLETE',record['unique_objects'],record['total_bytes'],flush=True)
