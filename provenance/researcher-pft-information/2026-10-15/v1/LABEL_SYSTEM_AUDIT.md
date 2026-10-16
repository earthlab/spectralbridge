# Canonical grouping and historical label audit

The only primary biological field is `cover_category`, with the five recorded
researcher categories. No inferred taxonomic grouping enters the new loader,
feature selectors, prediction labels, mixture fractions, primary figures or
scientific conclusions. A compatibility option in `load_compact_inputs` avoids
constructing historical labels at all for this workflow.

`label_system_inventory.csv` inventories textual references across package code,
examples, scripts, docs, notebooks, prior tables/builders and root final links.
`analysis_registry.json` is the explicit active/historical boundary. Legacy
inference/ML/report builders remain frozen and available for reproduction, not
silently rewritten or deleted. Scientific code shared with those analyses is
retained; a historical implementation is not the primary analysis merely because
it remains importable. Tests may retain historical synthetic fixtures.

Primary entry points, final root pointers and website pages now identify the
recorded researcher categories. Prior reports, including the two-label lab-story
and scientific-closure reports, are superseded for biological interpretation;
they remain historical evidence. Their historical lookup/sensor conclusions must
not be quoted as primary researcher-category findings. The older label crosswalk
and source taxonomic metadata are retained as provenance only.

The new report builder reads only the category-only v1 tables and checks their
class fields. A separate validation scans all primary tabular label values;
mentions of retired codes in this audit or historical warning are not results.
No notebook cells or historical figures/data were deleted. Generic processing,
NEON correction, sensor definitions and production defaults are unchanged.
