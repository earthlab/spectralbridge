"""Recheck physically staged temporary-cache objects against the transfer manifest."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=json.loads((P/'retrieval_manifest.json').read_text());out=[]
for r in rows:
 p=Path(r['local_path'])
 if not str(p).startswith('/private/tmp/spectralbridge-metashape-recovery-20261105/'):continue
 md5=hashlib.md5();sha=hashlib.sha256();size=0
 with p.open('rb') as f:
  while block:=f.read(8*1024*1024):md5.update(block);sha.update(block);size+=len(block)
 ok=size==r['bytes'] and md5.hexdigest()==r['checksum'] and sha.hexdigest()==r['sha256']
 out.append(dict(remote_path=r['remote_path'],bytes=size,verified=ok))
 assert ok,p
result=dict(objects=len(out),bytes=sum(x['bytes'] for x in out),all_verified=all(x['verified'] for x in out),legacy_manifest_entries_not_rechecked=len(rows)-len(out),files=out)
(P/'final_checksum_verification.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='files'})
