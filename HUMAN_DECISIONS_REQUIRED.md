# Human decisions required before publication

Reviewed 19 October 2026. These decisions cannot be inferred from tests, commit
counts, institutional logos or citation-schema validation. See
[the audit](PUBLICATION_READINESS_AUDIT.md) and the
[12-person comparison](provenance/publication-editorial/2026-10-19/v1/author_comparison.csv).

1. **Approve software and paper authorship separately.** Confirm each person's
   qualifying contribution, inclusion, exact spelling, order and consent. The
   paper/SI list Ty Tuff; Aashish Mukund; Nayani T. Ilangakoon; Erick Verleye;
   Megan E. Cattau; Janushi Shastri; Pavan Appanna; Tyler L. McIntosh;
   Matthew E. Bitters; Carol A. Wessman; Jennifer K. Balch; Cibele Amaral.
   Decide whether all, a subset, or additional contributors belong in the
   software citation, and who should instead be acknowledged. Commit counts
   cannot establish non-code contributions or consent.
2. **Approve metadata identities and contact roles.** Confirm affiliations,
   corresponding author and the meaning of organizational `Earth Lab` authorship
   in `pyproject.toml`. Decide whether separately named maintainers and a contact
   address should be published. Eight supplied ORCIDs have valid checksums and
   compatible public names; four are absent and optional, not invented. A
   conditional [CFF proposal](provenance/publication-editorial/2026-10-19/v1/CITATION.cff.proposed)
   assumes all 12 paper authors become software authors in that order; it is
   **not approved metadata** and must not be copied automatically.
3. **Declare funding and sponsor involvement.** Supply actual funding sources and
   award identifiers, and state sponsor roles, or explicitly confirm no financial
   support. Institutional affiliations and website logos are not funding evidence.
4. **Declare conflicts of interest.** Supply the authors' disclosure or confirm
   no relevant conflicts; do not derive a negative declaration from silence.
5. **Confirm the final AI responsibility declaration.** Authors must attest to
   human review, editing and validation of AI-assisted outputs and responsibility
   for core design decisions. The prompt log supports the recorded tool-use
   description but cannot certify this assertion or unknown historical models.
6. **Select the review/release identity and archive.** Choose the actual public
   commit/version for JOSS review and the release workflow. Confirm research-use
   evidence can be demonstrated to editors. Approve archival ownership and
   metadata, then verify the archive DOI for the reviewed release when required
   for JOSS acceptance. The 2024 pre-rename archive is not 2.3.0rc1. A matching DOI
   is not required merely to prepare the initial paper submission, and none has
   been invented here.
7. **Confirm rights and attribution sufficiency for release.** The files declare
   GPL-3.0-or-later and retain HyTools lineage. Maintainer/legal review must address
   any unresolved third-party code/data/figure rights; this audit makes no legal
   sufficiency judgment and proposes no license migration.

Separate community improvement: designate a private conduct/security reporting
route and responsible recipient(s). The Code of Conduct currently routes reports
to public issues despite a privacy obligation. No person's email was repurposed
as an incident contact without consent. This is flagged separately from the JOSS
funding/authorship/declaration gates.
