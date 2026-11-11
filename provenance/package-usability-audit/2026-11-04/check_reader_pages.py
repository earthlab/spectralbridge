"""Capture the built beginner path, retaining browser/rendering evidence."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
HERE=Path(__file__).resolve().parent
rows=[]
with sync_playwright() as p:
    browser=p.chromium.launch()
    for route,name,width,height in [('', 'home-desktop',1280,900),('getting-started/','getting-started-desktop',1280,1000),('getting-started/','getting-started-mobile',390,844),('vignettes/','workflow-map',1280,1000)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        response=page.goto('http://127.0.0.1:8878/'+route,wait_until='networkidle')
        page.screenshot(path=str(HERE/(name+'.png')),full_page=True)
        rows.append(dict(route=route,status=response.status,title=page.title(),viewport=[width,height],
            viewport_overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')))
        page.close()
    browser.close()
(HERE/'reader_pages.json').write_text(json.dumps(rows,indent=2)+'\n')
print(rows)
