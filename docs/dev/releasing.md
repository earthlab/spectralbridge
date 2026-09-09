# Releasing SpectralBridge

SpectralBridge releases use one immutable candidate: build the wheel and sdist
once, test those exact bytes, attach those bytes to GitHub, and publish the same
bytes to PyPI. Never rebuild between validation and publication.

Review date: 2026-09-08

## Version and tag contract

Synchronize all of these before tagging:

1. `pyproject.toml`
2. `src/spectralbridge/__init__.py`
3. `CITATION.cff` (top-level and preferred citation)
4. the first versioned heading in `CHANGELOG.md`
5. `uv.lock`

Final tags use `vMAJOR.MINOR.PATCH`. Prereleases use strict PEP 440 suffixes,
for example `v2.3.0rc1`, `v2.3.0b1`, or `v2.3.0a1`. Do not use
`v2.3.0-rc1` or `v2.3.0.rc1`.

Validate the candidate identity locally:

```bash
python scripts/check_release_metadata.py --tag v2.3.0rc1
```

## One-time PyPI and GitHub configuration

The repository workflow uses PyPI trusted publishing; it does not use a stored
API token.

Before pushing a release tag, a project owner must:

1. create or confirm the `spectralbridge` project on PyPI;
2. in PyPI project settings, add a trusted publisher with:
   - owner: `earthlab`
   - repository: `spectralbridge`
   - workflow: `release.yml`
   - environment: `pypi`;
3. in the GitHub repository, create the `pypi` deployment environment;
4. optionally add required reviewers to that environment so publication needs
   an explicit maintainer approval;
5. confirm GitHub Actions can create releases and request an OIDC identity token.

The workflow grants `id-token: write` only to the PyPI publication job and
`contents: write` only to the GitHub release job. All earlier jobs are read-only.

## Automated release gates

Pushing a matching tag, or deliberately dispatching the workflow with a tag,
runs these gates in order:

1. check version/tag synchronization;
2. run Ruff, the full source test suite, generated-evidence checks, link checks,
   and a strict documentation build;
3. build one wheel and one sdist and run `twine check`;
4. record SHA-256 checksums and upload one `release-candidate` artifact;
5. install the exact wheel outside the checkout on Python 3.10, 3.11, and 3.12;
6. install the exact sdist outside the checkout on Python 3.10;
7. run the bounded, offline installed-artifact smoke in every environment;
8. create a GitHub release using those artifacts, marking PEP 440 prereleases
   as GitHub prereleases;
9. publish the same wheel and sdist to PyPI through trusted publishing.

The build is never repeated in a downstream job. PyPI publication is last
because it is irreversible. If trusted publishing fails after the GitHub release,
fix the external configuration and rerun only the failed job so it downloads the
same retained candidate artifact.

## Installed-artifact smoke scope

The smoke uses tiny synthetic fixtures, blocks outbound network access, limits
parallelism and disk use, and runs outside the source checkout. It verifies:

- normal NEON stage orchestration and restart reuse;
- drone full and polygon extraction, corrections, QA, and no convolution;
- streaming bulk discovery, compact statistics, translation, LOSO, compact
  interpretation, and restart reuse without a pixel cache;
- spectral-library preflight and compact reporting;
- all release-critical public API imports, console scripts, and packaged data.

This is package and orchestration evidence, not production scientific
validation. Real-data evidence is maintained separately in the
[production validation record](production-validation-record.md).

## Local candidate checks

Run the source and documentation gates first:

```bash
ruff check src tests scripts
pytest -q
python scripts/generate_ai_transparency.py --check
python scripts/generate_validation_docs.py --check
python scripts/check_docs_links.py
mkdocs build --strict
```

Build into a clean directory and inspect both distributions:

```bash
python -m build
python -m twine check dist/*
python -m zipfile -l dist/spectralbridge-2.3.0rc1-py3-none-any.whl
python -m tarfile -l dist/spectralbridge-2.3.0rc1.tar.gz
```

For each required Python, create a fresh environment, install one exact local
artifact without editable/source-checkout leakage, run `pip check`, change to a
temporary directory, and execute `scripts/check_installed_artifact.py` with
`--expected-version 2.3.0rc1`.

## Recommended RC sequence

1. finish the local checklist and commit release preparation;
2. configure or verify the PyPI trusted publisher and protected GitHub `pypi`
   environment;
3. push the preparation commit and wait for branch CI;
4. create and push `v2.3.0rc1` from that exact commit;
5. approve the protected PyPI environment only after the artifact jobs pass;
6. verify the GitHub release is a prerelease with wheel, sdist, and checksums;
7. verify `https://pypi.org/project/spectralbridge/2.3.0rc1/` and install it in
   a fresh external environment;
8. ask external testers to run `examples/release_candidate_smoke.py` and one
   representative workflow appropriate to their data;
9. verify the archival/citation integration, including Zenodo when configured.

Do not publish a second build under the same version. If candidate contents
must change after publication, increment the prerelease number (for example,
`2.3.0rc2`).

## Dependency and artifact review

Release preparation must confirm that package data, console scripts, examples,
license, README, and citation metadata are present where intended. Dependency
removal is not a release-cleanup exercise: remove or move a runtime dependency
only with import/use evidence and exact-artifact tests. Defer speculative
dependency slimming to a separate change after the RC.
