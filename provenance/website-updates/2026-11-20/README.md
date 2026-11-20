# Website evidence snapshot — 20 November 2026

This compact publishing snapshot preserves source bytes and relative-path hashes
for the current HLS pure-pixel study, camera-position drone correction/translation,
mask comparison and BRDF benefit audit. It is not a new analysis. Original source
paths are recorded in manifest.json; raw imagery/ENVI are not copied here.
The HLS prediction CSV contains only the archived patch-level LOPO rows.
The numerical protocols and inference limits differ between studies.

scripts/generate_scientific_docs.py verifies each hash and copies these assets
into docs/ before the MkDocs build; --check rejects changed/missing outputs.
Scientific values are observations for this dated cohort, not package constants.
No independent purity, physical-reflectance accuracy or generalization claim is
created by publishing this evidence. Photos in the review PDFs remain dated
reference imagery; proposed labels await independent team review.

When replacing an analysis, make a new versioned snapshot with its source hashes,
update the scientific narrative and rerun generated-record/link/site checks.
Keep failed and unsupported cases visible. Full earlier investigation archives
remain separate; this snapshot does not overwrite them.
