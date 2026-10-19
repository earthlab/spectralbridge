# Final publication editorial audit — 19 October 2026

Start with root `PUBLICATION_READINESS_AUDIT.md`, `PUBLICATION_BLOCKERS.md`,
`HUMAN_DECISIONS_REQUIRED.md` and `publication_readiness.json`. This packet is
editorial/metadata/build evidence, not a new scientific analysis or a release.

- `SURFACE_MAP.md`: reader-facing responsibility map and editing plan.
- `documentation_inventory.json`, `placeholder_audit.json`, `TERMINOLOGY.md`:
  current/specialized/history distinction, all active Markdown sources and terms.
- `author_comparison.csv`, `orcid_public_records.json`: all twelve paper authors,
  contributor evidence, public ORCID checks and unresolved software authorship.
- `CITATION.cff.proposed`: **conditional** exact CFF proposal, assuming all twelve
  paper authors are approved for software citation in that order. Not approved.
- `cff_validation.json`, `cff-1.2.0-schema.json`: official schema and syntax checks;
  they cannot certify authorship. Schema source is the official CFF1.2 repository.
- `citation_audit.json`: 166 main/SI entries, 52 DOI registry records, citation
  contexts, descriptive relevance limits, provider failures/retries and title note.
- `official_requirements.json`, `external_records.json`: dated official JOSS,
  PyPA/PyPI, CFF/GitHub, Zenodo and SPDX references plus retrieved public metadata.
- `distribution_metadata.json`: final wheel/sdist hashes, actual headers and file
  inventories. Candidate artifacts are retained in ignored
  `dist/publication-editorial-2026-10-19/`, not uploaded or tagged.
- `release_installed_smokes.json` and `release-*-smoke.log`: the final candidate
  wheel3.10/3.11/3.12 and sdist3.10 checks. Earlier `installed_smokes`/`final_installed`
  records describe exploratory candidates invalidated by later editorial/test
  changes; they are not the final reviewed bytes.
- `joss_build_attempt.json`, `joss-build.log`, `fresh_paper_validation.json`:
  successful official pinned-image build from isolated copies, network disabled,
  ten pages and text comparison to the recorded preview. A runtime ticker message
  was printed despite exit0; complete output was independently checked.
- `website_render_checks.json`, `pypi_render_checks.json`, `pypi-readme.html`:
  actual local browser and actual built-description checks. Screenshots remain
  under `/private/tmp/p139-web-review/`; the reviewed fresh PDF is under
  `output/pdf/publication_editorial/JOSS-preview.pdf`.
- `pytest-initial.log`, `pytest-final.log`: initial documentation-contract failure
  and repaired broad-suite result, rather than hiding the first failure.
- `historical_hashes.json`, `preservation_validation.json`: protected dated/history/
  formal bytes; mutable prompt/queue/top-level provenance index explicitly excluded.
- `packet_manifest.json`: final owned audit file hashes; approval still outstanding.

## Reproduction boundaries

Run normal repository commands listed in the root audit. Network checks use
public DOI/ORCID/PyPI/GitHub/Zenodo APIs; saved responses make the dated observations
inspectable without pretending they remain current forever. CFF validation used
`jsonschema.Draft7Validator` on the stored official1.2 schema and parsed YAML.
The PDF renderer and exact Docker invocation are recorded, not replaced with an
unofficial typesetting approximation. Do not run historical scientific stage
scripts to reproduce this editorial audit.

The final artifact matrix used fresh temporary environments and the production
`scripts/check_installed_artifact.py` outside the checkout. Network is disabled
inside that bounded smoke. Dependency installation was permitted before the
smoke; no secret credentials or external messages were used.

This packet does not resolve source scale for P138, establish field abundance,
choose authors or declare a release. Human decisions are recorded in the root
file, rather than buried among passing automated checks.
