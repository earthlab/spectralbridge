"""Collect audit evidence without converting partial verification into release approval."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def suite(path):
    root=ET.parse(path).getroot()[0]
    cases=root.findall('testcase')
    failures=[dict(test=t.attrib['classname']+'.'+t.attrib['name'],reason=t.find('failure').attrib.get('message')) for t in cases if t.find('failure') is not None]
    return dict(collected=int(root.attrib['tests']),passed=int(root.attrib['tests'])-int(root.attrib['failures'])-int(root.attrib['errors'])-int(root.attrib['skipped']),failures=int(root.attrib['failures']),errors=int(root.attrib['errors']),skipped=int(root.attrib['skipped']),failure_details=failures)

checks=dict(baseline=suite('/private/tmp/p178-baseline.xml'),final_source_suite=suite('/private/tmp/p178-audit-final.xml'),final_focused=suite('/private/tmp/p178-final-focused.xml'),additional_targeted=suite('/private/tmp/p178-targeted-final.xml'),browser=suite('/private/tmp/p178-browser-final.xml'),
    entrypoint_runs=24,entrypoint_failures=0,primary_console_scripts=11,legacy_aliases=6,remote_subcommand_help_pages=3,
    strict_mkdocs='PASS',rendered_api_signatures=393,docs_links='PASS',ruff='PASS',standard_pip_install='PASS; clean Python 3.12 venv; editable source',pip_dependency_check='No broken requirements found',installed_workflow_smoke='PASS; non-editable temporary installation; network blocked; tiny synthetic inputs',
    release_status='NOT_READY: broad regression gate remains red; actual checkout still 2.3.0rc1',camera_tables='Five discovered and checksum-verified; Goldhill declared CRS discrepancy retained; no source overwritten')
checks['all_final_failures_observed_in_baseline'] = {r['test'] for r in checks['final_source_suite']['failure_details']} <= {r['test'] for r in checks['baseline']['failure_details']}
assert checks['all_final_failures_observed_in_baseline']
(HERE/'final_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
for source,name in [('/private/tmp/p178-baseline.xml','tests-baseline.xml'),('/private/tmp/p178-audit-final.xml','tests-final-source.xml'),('/private/tmp/p178-audit-final.log','tests-final-source.log'),('/private/tmp/p178-final-focused.xml','tests-final-focused.xml'),('/private/tmp/p178-targeted-final.xml','tests-additional-targeted.xml'),('/private/tmp/p178-browser-final.xml','tests-browser.xml'),('/private/tmp/p178-browser-final.log','tests-browser.log'),('/private/tmp/p178-final-installed.log','installed-workflow-smoke.log'),('/private/tmp/p178-documented-pip-install.log','documented-pip-install.log'),('/private/tmp/p178-pip-check.log','pip-check.log'),('/private/tmp/p178-analysis-lesson.log','analysis-lesson.log'),('/private/tmp/p178-docs-audit-final.log','docs-strict.log'),('/private/tmp/p178-rendered-api-final.log','rendered-api.json'),('/private/tmp/p178-links-final.log','docs-links.log'),('/private/tmp/p178-final-ruff.log','ruff.log'),('/private/tmp/p178-header-red.log','header-regression-before-fix.log')]:
    if Path(source).exists():shutil.copyfile(source,HERE/name)
full=checks['final_source_suite']
text=f'''- Clean standard-venv/pip source installation and offline lessons: **passed**; dependency check: **no broken requirements**.
- Installed stage-complete synthetic NEON, drone/full/polygon/translation, bulk/restart and library checks: **passed**; six changed runtime-module hashes exactly match the tested non-editable installation.
- Final focused regression set: **{checks['final_focused']['passed']} passed**. An additional overlapping API/numerical/producer set had **{checks['additional_targeted']['passed']} passed**; these counts are not additive unique coverage.
- Browser checks: **{checks['browser']['passed']} passed**; four desktop/mobile reader captures inspected, no page-wide overflow.
- All **17 CLI help interfaces**, three remote subcommand help pages and four beginner/configuration entry points: **24 successful runs**.
- Strict docs, **393 rendered API signatures**, repository link checks, API freshness, Ruff and generated transparency: **passed**.
- Broad final source gate: **{full['passed']} passed, {full['failures']} failed, {full['skipped']} skipped, {full['errors']} errors**. This is deliberately **not** reported as a green suite. Failures and exact test names are retained in [final_checks.json](provenance/package-usability-audit/2026-11-04/final_checks.json) and the source JUnit/log evidence.
'''
p=ROOT/'PACKAGE_USABILITY_AUDIT.md';s=p.read_text();a=s.index('<!-- AUDIT:FINAL_CHECKS -->');b=s.index('\nThe broad source run',a);s=s[:a]+'<!-- AUDIT:FINAL_CHECKS -->\n'+text+s[b:];p.write_text(s)
print(json.dumps({k:checks[k] for k in ['final_source_suite','final_focused','browser']},indent=2))
