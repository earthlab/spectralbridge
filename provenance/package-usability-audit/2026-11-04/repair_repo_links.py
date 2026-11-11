"""Keep retained evidence links usable on the built site, without moving files."""
import json,re
from pathlib import Path
from urllib.parse import unquote,quote,urlsplit
ROOT=Path(__file__).resolve().parents[3]
DOCS=ROOT/'docs'
changes=[]
for file in DOCS.rglob('*.md'):
    text=file.read_text()
    def repair(match):
        url=match.group(1)
        if urlsplit(url).scheme or url.startswith(('#','/','<')):return match.group(0)
        path,sep,fragment=url.partition('#')
        target=(file.parent/unquote(path)).resolve()
        if not target.exists() or not target.is_relative_to(ROOT) or target.is_relative_to(DOCS):return match.group(0)
        relative=target.relative_to(ROOT).as_posix()
        kind='tree' if target.is_dir() else 'blob'
        destination=f'https://github.com/earthlab/spectralbridge/{kind}/main/{quote(relative,safe="/")}'
        if sep:destination+='#'+fragment
        changes.append(dict(page=str(file.relative_to(ROOT)),before=url,after=destination))
        return ']('+destination+')'
    revised=re.sub(r'\]\(([^\s)]+)\)',repair,text)
    if revised!=text:file.write_text(revised)
record=ROOT/'provenance/package-usability-audit/2026-11-04/docs_link_repairs.json'
if changes or not record.exists():
    prior=json.loads(record.read_text()) if record.exists() else []
    record.write_text(json.dumps(prior+changes,indent=2)+'\n')
print(len(changes),'links repaired in',len({x['page'] for x in changes}),'pages')
