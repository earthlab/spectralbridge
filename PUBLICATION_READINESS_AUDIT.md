# SpectralBridge final publication editorial audit

Review date: **19 October 2026**. Baseline: main, `38f646a` (`mesma reports`).
Scope: editorial organization, publication metadata and technical verification;
no new science, package refactor, license change, tag, upload or submission.
The earlier P138 stopped-audit changes were present and preserved.

## EXECUTIVE STATUS

**Technical checks pass; unconditional publication approval is blocked by human
metadata/declarations, the choice of reviewed release/archive, and disposition
of the existing P133 implementation findings.** A stranger
now has a shorter README, a source-install path that works without an unavailable
PyPI project, clearer current-versus-historical evidence, citation limitations and
explicit publication decisions.

Start with [PUBLICATION_BLOCKERS.md](PUBLICATION_BLOCKERS.md) and
[HUMAN_DECISIONS_REQUIRED.md](HUMAN_DECISIONS_REQUIRED.md).
[publication_readiness.json](publication_readiness.json) is the machine-readable
status summary. The [dated evidence directory](provenance/publication-editorial/2026-10-19/v1/SURFACE_MAP.md)
contains the inventory, source URLs, author comparison, citation audit, artifact
metadata/hashes and build/render records.

| Milestone | Assessment |
| --- | --- |
| Public documentation | PASS WITH EDIT: build, links and rendered routes checked; provisional citation/release status remains explicit. This is not blanket publication approval. |
| PyPI RC | NEEDS HUMAN CONFIRMATION: exact artifact checks pass; authorship, intended public candidate and release approval remain open. |
| Final PyPI release | BLOCKING: current identity is 2.3.0rc1, not a final version; author/release decisions are unresolved. |
| JOSS submission | BLOCKING: formatting/build pass, but consent, funding/sponsor, COI and final AI declarations are incomplete. A matching release archive is needed at acceptance, not invented as an initial-submission prerequisite. |

## WEBSITE

The existing Home → Understand → Use → Spectral Library → Validate → Reference →
Develop architecture already works. **No navigation/folder redesign was made.**
The homepage now exposes source setup, API and citation routes; its setup links
were corrected after visual review found poor contrast against the hero.
The synthesis links directly to the selected-library exhaustive MESMA result and
keeps difference → identity → quantity → uniqueness → field validation separate.

Twelve important routes were rendered at desktop and mobile widths: home, getting
started, workflow choice, synthesis, abundance/ambiguity, mathematics, validation,
scientific API, contributing, citation and release guidance. All 24 render checks
have no broken article images or horizontal page overflow. Mobile tables still
need sideways scrolling and dense API tables are a usability improvement area;
that is not hidden by the overflow check. Major headings, setup instructions,
science bodies, citation guidance and figure/caption layout were visually checked.

## README

Replaced the long researcher-analysis/chronological tail with a compact entry
point covering purpose/audience, install/verify, workflows, QA, API, citation,
contribution, license and evidence. Detailed results remain on the website and
in preserved packets. All 27 README links are absolute HTTPS links suitable for
GitHub, PyPI and the sdist.

The current PyPI project endpoint returned **404**, so active installation pages
now use the source checkout rather than presenting an unavailable distribution
as installable. Distribution/import identities remain `earthlab-spectralbridge`
and `spectralbridge`. The wheel's actual UTF-8 long description matches this
README, passes `twine check`, and was rendered with `readme_renderer[md]` and
inspected at desktop/mobile widths. Its citation paragraph explicitly identifies
unapproved metadata instead of manufacturing a finalized citation.

## DOCUMENTATION ORGANIZATION

The [surface map](provenance/publication-editorial/2026-10-19/v1/SURFACE_MAP.md)
assigns responsibility to user entry points, scientific documentation, API,
validation/evidence, developer, publication, historical and maintainer surfaces.
All **115 Markdown sources** under active `docs/` were inventoried, including
**34 non-navigation sources**. Historical reports and generated include snippets
are distinguished from current instructions; the existing page catalog and
landing links preserve specialized routes. Include-only `_closure`, `_snapshot`
and `_transfer` snippets are not ordinary orphan tutorials.

Corrected stale “RSE manuscript” wording that implied publication; the software
paper is a prepared source, not an accepted article. Citation-guide TODO rows
were replaced by factual status or an existing canonical paper link. No scientific
numbers, historical grouping results, generated SI content or frozen figures
were rewritten. All 30 root exports are present and mentioned in the rendered
API reference; the source-only text scan correctly distinguishes autogenerated
reference content from literal Markdown mentions. Experimental numerical
methods retain their existing maturity and analytics-extra instructions. The terminology dictionary records deliberate differences such
as synthetic OLI versus actual Landsat and recognition versus inverse uniqueness.

## DIRECTORY FINDABILITY

Existing READMEs already cover paper, archive, examples, tests, scripts, formal
and provenance; `docs/index.md` is the documentation landing page. Additional
README files were **not mechanically added**. Expanded `examples/README.md` to
identify the tiny offline lessons and warn that research runners regenerate
outputs. Expanded `provenance/README.md` with the canonical researcher evidence,
its numerical companion, selected-reference tests, exhaustive experiment and
stopped information-experiment audit. Dated packets remain evidence, not the
current user manual.

## PYPI

Added the existing Changelog URL to project metadata. The built wheel/sdist have
version 2.3.0rc1, the correct distribution identity, Python requirement, SPDX
GPL-3.0-or-later expression, LICENSE/NOTICE, extras, scripts and package data.
Actual metadata and complete file inventories are saved in
`distribution_metadata.json`. Organizational author `Earth Lab` remains unchanged
because evidence does not establish whether it was deliberate or provisional;
no maintainer identity/email was invented.

Final audit-candidate bytes are retained under
`dist/publication-editorial-2026-10-19/` (ignored build outputs), with hashes in the
machine-readable audit. The exact wheel passed the offline installed-artifact
smoke on **Python 3.10, 3.11 and 3.12**; the exact sdist passed on **Python 3.10**
in fresh temporary environments outside the checkout. Earlier exploratory
artifacts were invalidated by later test/contrast edits and are not the final
candidate. No bytes were uploaded or promoted to a release.

## JOSS

The existing manuscript is already a restrained software paper with all eight
required sections, three figures and specific team research-use examples. It
avoids claiming external adoption or independent cross-sensor/field accuracy.
The current source checker reports **1,647 words including captions** (1,415
without), within JOSS's current 750–1750 guidance. All **65 main-paper citation
keys** resolve; the separate 13,542-word SI is not counted as the short paper.
[Official paper guidance](https://joss.readthedocs.io/en/latest/paper.html).

A fresh PDF was built from isolated copies using the pinned official
`openjournals/inara` image with container networking disabled. Docker initially
was not running; starting installed Docker Desktop resolved that. The build
returned success and produced ten pages whose extracted text matches the
recorded preview. All ten fresh pages were rendered and visually inspected.
Draft watermark/DOI/editor/date placeholders belong to the preview template;
author-input placeholders are real submission blockers. The existing preview
and historical build records were not overwritten.

Research-use statements remain about developer-team workflows, including missing
production provenance explicitly acknowledged in the paper. Public releases
provide historical evidence, but authors must select the actual review source
and demonstrate any private workflow evidence to editors. This simulated review
is not an eligibility decision or an actual message to JOSS reviewers.

## AUTHORS

Paper and SI have identical **12-person author lists and six affiliations**.
The [person-by-person table](provenance/publication-editorial/2026-10-19/v1/author_comparison.csv)
records exact spellings, order, affiliations, corresponding-author flag,
contributor evidence, CFF/PyPI presence, ORCIDs and required confirmations.

The exact inconsistency is: **12 named people in the paper; “Earth Lab /
SpectralBridge Team” encoded as a person-like CFF placeholder, duplicated in
preferred-citation; only “Earth Lab” in package author metadata.** No canonical
software author list or separate maintainer list is established. Git aliases
support some contribution associations, but do not establish eligibility or
justify excluding non-code contributors.

All eight supplied ORCIDs pass checksum checks and return compatible public
given/family names. Missing middle initials in a public ORCID name were not
“corrected”; four missing ORCIDs are optional. Current affiliations and consent
remain author decisions. Ty Tuff is marked corresponding author in supplied
paper metadata, not automatically appointed as private incident contact.

The 2024 Zenodo archive has a different historical creator list, including both
`Janushi Shastri` and `JanushiShastri2001`, and historical affiliation wording
“Environmental Data Science Innovation and Inclusion Lab.” The current paper
uses Innovation & Impact Lab. These differences are recorded, not silently
reconciled or copied into current metadata.

The current CFF and a conditional exact 12-author proposal both validate against
CFF 1.2's official schema. **Schema validity is not author approval.** The proposal
is clearly marked conditional and omits invented DOI/release-date information.
Current CFF TODO comments remain an explicit publication blocker; they were not
removed to make unresolved authorship look finished.

## CITATIONS

The machine-readable audit inventories **166 main/SI bibliography entries and
52 distinct DOI records**, with citation contexts, registry metadata, same-file
duplicate checks and relevance/interpretation notes. All 52 DOI records were
retrieved from Crossref/DataCite, using a DOI-filtered Crossref query for two
records after direct-endpoint failures. Provider HTTP403/202 responses are retained
as access limitations, not mislabelled dead DOIs. Methods/software references do
not establish SpectralBridge empirical validation. Pinned repository references
retain the cited revision; historical local evidence is not assigned an invented DOI.

No new DOI/author/year correction was justified by the fresh metadata audit.
One recorded title variant is descriptive HyTools: Hyperspectral image processing
library versus the registered title HyTools (same version/DOI/creators). This is
flagged as optional exact-title normalization; the existing canonical bibliography
and preserved SI rendering were not silently rewritten. Long internal evidence
references contribute to the ten-page preview and could be consolidated later
with author/editor agreement, without deleting provenance.

## FUNDING

Acknowledgements still request financial support/award and sponsor-role input.
No award number or “no funding” declaration was invented. Affiliation, institution
logos, acknowledgements, financial support and software lineage remain separate.
JOSS also requires sponsor involvement disclosure where applicable.
[Official submission policy](https://joss.readthedocs.io/en/latest/submitting.html).

## AI DISCLOSURE

The paper already describes known tools, requested assistance and missing
historical model identities. The generated transparency page is refreshed from
the verbatim prompt log. Neither proves that every requested check occurred or
that humans reviewed all AI output. The final human review/edit/validation and
core-design declaration remains open, as required by the
[current JOSS policy](https://joss.readthedocs.io/en/latest/submitting.html#ai-usage-policy).
No human confirmation was inferred or supplied on the authors' behalf.

## LICENSE

LICENSE, NOTICE, HyTools provenance, project SPDX metadata, README and current
paper consistently describe GPL-3.0-or-later. Conditional future Apache references
are warnings/checklist history, not claims that migration occurred. No license
change or legal sufficiency judgment was made. Maintainers retain responsibility
for third-party/data/figure rights and distribution approval.

## COMMUNITY/GOVERNANCE

CONTRIBUTING and the Code of Conduct already provide contribution/test routes.
Corrected prerelease tag wording, exact GPL identifier and stale instructions to
move historical material into `deprecated/`. Added concise bug/documentation
issue templates and a PR template that requests actual verification and evidence
boundaries. They add no invented maintainers or mandatory bureaucracy.

The Code of Conduct currently directs reporting to public issues despite a
privacy obligation, and no private security policy/contact was found. A private
reporting route needs human designation; no person's address was reassigned.
This is recorded as a community improvement, separately from required authorship
and JOSS declarations.

## VERSION/RELEASE

| Surface | Observed identity/status |
| --- | --- |
| Repository baseline | main at 38f646a, plus documented local edits; no new commit made |
| Project/package/CFF/preferred citation/first changelog heading | 2.3.0rc1; synchronization check passes |
| Local tags | 0.1 and v1.0.0; no 2.3.0rc1 tag |
| GitHub releases API | 0.1 prerelease (25 March 2024); v1.0.0 (9 May 2024) |
| PyPI earthlab-spectralbridge API | HTTP404 on review date; no current release inferred |
| Zenodo record11167877 | earthlab/cross-sensor-cal: Version1, versionv1.0.0, DOI10.5281/zenodo.11167877 |
| Paper revision | 12 October 2026; prepared, not verified submitted/accepted |
| JOSS review version/current archive | Human selection and subsequent archive verification required |

The legacy conda label is explicitly identified as such; it was not renamed
under existing users. Release docs preserve one tested immutable final candidate,
trusted publication and strict PEP440 tags. No final version was chosen merely
because tests pass.

## DOI/ARCHIVE

Verified the historical Zenodo record and corrected citation/DOI guidance to
separate it from the current candidate. No `.zenodo.json` override was found.
CFF/GitHub citation behavior and Zenodo metadata ingestion are documented in the
[official sources registry](provenance/publication-editorial/2026-10-19/v1/official_requirements.json).
The paper DOI, software version DOI and concept DOI identify different objects.
A new archive must be checked for authors/title/version/license and reviewed
source identity at the appropriate release/acceptance stage.

## TEST/BUILD STATUS

| Check | Result |
| --- | --- |
| Broad feasible pytest | 749 passed, 7 skipped, 2 full/network/browser cases deselected; 30 warnings |
| Initial broad run | 746 passed, one stale notebook-directory contract failed; repaired to accept existing canonical GitHub example notebooks without allowing static/broken links |
| Ruff | `ruff check src tests scripts` passes |
| Strict MkDocs; source and built links | Pass; built internal-link/anchor/asset check has zero errors |
| Scientific/validation/SI/transparency generators | Freshness checks pass; no scientific regeneration |
| Package wheel/sdist; twine | Pass on final candidate; actual metadata/file lists retained |
| Exact installed artifacts | Wheel3.10/3.11/3.12 and sdist3.10 pass bounded offline smoke outside checkout |
| JOSS source/reference checks | Pass; `--ready` fails as intended on missing author declarations |
| Official JOSS PDF build | Fresh successful ten-page build; text matches previous preview; visually reviewed |
| CFF1.2 schema | Current and conditional proposal pass; approved authorship remains open |
| Website/PyPI renders | 24 site renders plus desktop/mobile built-description renders checked |
| Historical preservation | 1,861 protected provenance/archive/formal files unchanged; mutable index/queue/prompt explicitly excluded |

The broad suite excludes external/full datasets and browser-marked tests;
the local desktop/mobile browser audit was executed separately. Scientific
integration checks retain canonical numbers and figure hashes. No new field
validation, production archive run or mathematical proof is claimed.

## BLOCKERS

See the short [blocker list](PUBLICATION_BLOCKERS.md), restricted to actual
publication gates. Approved authorship, declarations, public review/release identity and the
disposition of known P133 implementation defects are unresolved. Archive verification is required for the eventual
archived release/JOSS acceptance. P138's source-scale gate remains visible but
was not misused to block editorial work.

## NON-BLOCKING IMPROVEMENTS

Consider reducing internal-reference density with author/editor agreement,
improving narrow-screen API-table navigation, and adding a private conduct/
security reporting route. Optional absent ORCIDs are not invented blockers.
P133 still records reproduced band-axis inference and overlapping extraction
windows; the corresponding source expressions remain present. A final stable
release needs focused fixes or explicit justified support restrictions, plus a
source-impact assessment before regenerating historical science. Passing bounded
fixture tests is not evidence that those known defects disappeared. No new
analysis of the same spectra is needed to finish this editorial pass.

## Official requirements and reproduction

Official sources were reviewed on **19 October 2026** and recorded with URLs in
`official_requirements.json`: JOSS submission/paper/review/checklist and AI/
authorship policy; Python Packaging User Guide/current pyproject specification;
PyPI metadata; PEP621; CFF1.2; GitHub citation behavior; Zenodo archiving/metadata;
and the SPDX GPL identifier. Existing repository checklists were not treated as
proof that external requirements were current.

Commands used include:

```bash
ruff check src tests scripts
python -m pytest -m 'not full and not network and not playwright'
mkdocs build --strict --site-dir /private/tmp/p139-site
python scripts/check_docs_links.py
python scripts/check_built_site.py /private/tmp/p139-site
python scripts/generate_scientific_docs.py --check
python scripts/generate_validation_docs.py --check
python scripts/generate_supplement_docs.py --check
python scripts/generate_ai_transparency.py --check
python scripts/check_release_metadata.py --tag v2.3.0rc1
python -m build --no-isolation --outdir /private/tmp/p139-release-dist
python -m twine check /private/tmp/p139-release-dist/*
python scripts/check_joss_submission.py
python scripts/check_joss_submission.py --ready
```

The isolated official Docker invocation, final artifact SHA256s, fresh interpreter
versions, smoke commands/logs and browser checks are in the dated packet. The
normal JOSS source remains unchanged; official compile inputs were copied into
a temporary directory to preserve the recorded preview. This report records
an audit, not a release, submission, consent statement or legal certification.
