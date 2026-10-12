# JOSS submission checklist

Checked against the official guidance on 12 October 2026:

- [Submission requirements](https://joss.readthedocs.io/en/latest/submitting.html)
- [Paper format](https://joss.readthedocs.io/en/latest/paper.html)
- [Review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html)

**Current status: formatting prepared; author declarations and public upload remain.**
A successful preview build is not a declaration that all submission gates are met.

## Prepared and checked

| Requirement | Evidence / status |
| --- | --- |
| Markdown paper in the software repository | `paper/paper.md`, bibliography and figures prepared locally; publish the reviewed changes before submitting. |
| Required sections and YAML metadata | All eight paper sections present; 12 author names, six affiliations, eight supplied ORCIDs with valid checksums. |
| Short software paper | Source word-count check includes captions and excludes citation keys/math; see `generated/submission-checks.json`. Software design, need, and reuse remain the focus; examples retain their limitations. |
| References and internal links | All manuscript citation keys resolve; DOI-backed references checked against DOI registry/publisher metadata; URLs repaired from PDF extraction. See `bibliography-audit.json`. |
| PDF compilation | Official `openjournals/inara` build completed locally; inspect `generated/paper.pdf` and `generated/build-verification.json`. Draft DOI/editor/date placeholders and watermark belong to the official template. |
| Repeatable build | `.github/workflows/joss-paper.yml` uses the same pinned image digest, checks source contracts, and uploads the preview. This new workflow has not yet run on GitHub. |
| Source availability | [Public GitHub repository](https://github.com/earthlab/spectralbridge), browsable source and [issue tracker](https://github.com/earthlab/spectralbridge/issues) observed. |
| Open-source license | Actual `LICENSE`, GPL-3.0-or-later package metadata, `NOTICE`, and `HYTOOLS_PROVENANCE.md` are present. No licensing change is made here. |
| Installation, examples, tests and contribution paths | `README.md`, `pyproject.toml`, `tests/README.md`, examples, CI workflows, `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md` present. Existing scientific test results are not reasserted as a fresh full-suite run. |
| Iterative development | Local history spans April 2025–September 2026; [public release](https://github.com/earthlab/spectralbridge/releases) and [PR history](https://github.com/earthlab/spectralbridge/pulls?q=is%3Apr+is%3Aclosed) are visible. Commit dates alone do not establish the date a repository became public. |
| Research use | Main paper describes developer-team R10C and bulk workflows, with incomplete drone-production evidence identified explicitly. No external adoption, independent accuracy, or new benchmark claim is added. |
| Supporting material | SI retained separately as repository support. The 44-page source PDF is authoritative for complex table layout; it is not included in the short JOSS paper build. |

## Author decisions required before submitting

- [ ] Confirm all listed authors consent and have qualifying software/project
  contributions under JOSS's authorship policy; the submitting author must be a
  major contributor with a GitHub account.
- [ ] Provide funding/award information and sponsor involvement, or confirm no
  financial support. Replace the explicit author-input marker in Acknowledgements.
- [ ] Provide conflicts-of-interest disclosures, or confirm no relevant conflicts.
- [x] Fill recorded AI systems, model labels, requested assistance, verification
  scope, and missing-metadata limitations from the prompt log.
- [ ] Confirm human review, editing, validation of all AI-assisted outputs, and
  human responsibility for core design decisions. The prompt log cannot attest
  to this; missing historical model versions remain explicitly unrecorded.
- [ ] Choose the software branch/commit/version to be reviewed. Current package
  metadata is `2.3.0rc1`; local HEAD before these edits is
  `7e934bc273b7bf440b49c485d47da72a9b580f66`; existing public release evidence
  identifies `v1.0.0`. These identities must not be conflated.
- [ ] Confirm more than six months of *public* development, using public releases,
  discussions and repository visibility history as appropriate. The manuscript
  preparation does not itself certify eligibility.
- [ ] Confirm the documented research-use evidence is accessible to the editors
  or identify how author-supplied/private workflow evidence can be demonstrated.
  Supply any related published, submitted, or forthcoming papers for the form;
  do not invent publications or external users.
- [ ] Have a colleague try the documented install and representative workflow,
  if that has not already been recorded.
- [ ] Review the compiled paper, author metadata, corrected references, and SI.
  Bibliography corrections include publisher-record author names that differ from
  the original PDF; the originals remain unchanged for comparison.

## Public submission steps

1. Finish the declarations above and rerun:

   ```bash
   python scripts/check_joss_submission.py --ready --output paper/generated/submission-checks.json
   pytest -q tests/test_joss_submission.py tests/test_ai_transparency.py
   ```

   `--ready` checks manuscript declarations as well as format. It cannot certify
   consent, public history, research impact, release publication, or editor decisions.

2. Commit and push the reviewed paper, bibliography, figures, supporting material,
   validator/tests, workflow and prompt-transparency artifacts to a public Git
   branch containing the software. Check the new JOSS paper workflow and download
   its preview artifact. No commit, push, release or submission was made here.
3. Record the resulting public branch/commit and `paper.md` location. The local
   prepared path is `paper/paper.md`; the repository is
   `https://github.com/earthlab/spectralbridge`.
4. The submitting author completes the [JOSS form](https://joss.theoj.org/papers/new),
   provides the review version and associated-publication disclosures, and
   participates in the public review through their GitHub account.
5. Use a release archive/DOI that identifies the reviewed software when requested
   during final review. The historical pre-rename Zenodo DOI is not an archive of
   the current candidate. Follow `docs/dev/doi-zenodo.md` and
   `docs/dev/releasing.md`; do not fabricate or reuse a mismatched identifier.

JOSS permits disclosed AI assistance with software and paper preparation, but
forbids AI-generated conversational interactions with editors/reviewers except
translation. The authors should conduct those interactions themselves. This
checklist is preparation material, not an editor/reviewer message.
