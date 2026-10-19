# Publication blockers

Reviewed 19 October 2026. This file lists unresolved publication gates, not every
optional improvement or scientifically unestablished application.

| Gate | Affected milestone | Required resolution |
| --- | --- | --- |
| Canonical authorship is unapproved | Software citation, publication metadata, JOSS | Reconcile 12 paper authors, placeholder team CFF and organizational PyPI author; obtain qualification/order/consent/affiliation confirmation. Current CFF still has two TODO comments. |
| Required author declarations remain blank | JOSS submission | Complete funding/sponsor, COI and human AI review/design declarations. The format check passes; `check_joss_submission.py --ready` correctly fails. |
| Reviewed public source/release identity has not been selected for this audit | RC/final release and JOSS review | Approve the actual public commit/version and run applicable CI for those exact bytes. Local metadata is 2.3.0rc1; published GitHub releases found are historical 0.1/v1.0.0. PyPI returns 404 for earthlab-spectralbridge at the audit date. |
| No verified archive of the current reviewed release | Archived release / JOSS acceptance | When final review requires it, create/verify an archive matching the approved version/authors/license. Do not reuse the pre-rename DOI. This is not falsely presented as a prerequisite to an initial JOSS submission. |
| Known scientific I/O defects remain queued in P133 | Final stable release / unqualified functionality claims | Resolve or formally restrict supported inputs for the reproduced small-cube brightness-axis and overlapping extraction-window defects; assess source lineage before any historical regeneration. This editorial task does not patch them. |
| Outstanding release attestations | Release approval | Confirm licensing/third-party/data/figure rights and research-use/public-history evidence where maintainer/editor judgment is required. Technical checks do not supply these declarations. |

The source-scale condition blocking P138's new scientific experiment is preserved,
but is **not** treated as a blanket blocker to documenting or distributing the
software with its existing conditional claims. Independent field abundance is
not established; that is a scientific scope limit, not a requirement invented for
this software-paper submission.

Build/test results and any execution limitations are recorded in
[PUBLICATION_READINESS_AUDIT.md](PUBLICATION_READINESS_AUDIT.md) and
[publication_readiness.json](publication_readiness.json). No release, tag, archive
upload, JOSS submission or PyPI upload was made.
