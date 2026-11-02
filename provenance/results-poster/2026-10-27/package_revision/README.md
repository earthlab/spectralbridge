# White package-functions poster

36 x 48 inch portrait poster, white background. Rebuild with `python provenance/results-poster/2026-10-27/package_revision/build_poster.py` using ReportLab and pypdf. It reuses the existing native-resolution visible/NIR image assets; no data processing is rerun. Earlier posters remain intact.

The core four-stage NEON explanation follows README.md, docs/pipeline.md and package exports: prepare flightlines, BRDF/topographic correction, configured target-band weighting, and tabular export/QA. Supported local drone processing is explicitly a separate route. Downstream bulk comparisons read completed products using compact statistics; library reporting is another separate entry point. Entry-point names were checked against src/spectralbridge/__init__.py and the corresponding local vignettes. The imagery is explicitly illustrative: two channel combinations of the same corrected image, not correction efficacy or independent sensor validation.

The original imagery manifest records exact selected wavelengths, display stretches, source SHA256 and native dimensions. This revision adds source hashes, output hash and layout boxes. Print imagery remains at approximately 162 native pixels per inch at full poster size; labels and graphics are vector content.

Verification: one-page dimensions, all four core headings, public entry-point labels, caveats and page/card text widths pass. Full-page Poppler render visually inspected: white background, complete image extents, readable hierarchy and no overlapping or clipped text. Documentation and repository links are clickable. No package behavior changed; package tests were not needed.
