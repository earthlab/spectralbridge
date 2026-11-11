"""Resume independent three-site correction stages as geometry becomes ready."""
import json,time
from correct_sites import site
from prepare_rerun import HERE,WORK
for config in json.loads((HERE/'site_inputs.json').read_text()):
    marker=WORK/config['site'].lower()/'geometry_complete.json'
    checks=0
    while not marker.exists():
        if checks%10==0:print(config['site'],'waiting for bounded geometry stage',flush=True)
        time.sleep(3);checks+=1
    site(config)
