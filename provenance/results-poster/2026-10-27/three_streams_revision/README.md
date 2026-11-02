# Three-input-stream poster

White 36 x 48 inch poster. The user confirmed three streams: NEON flightlines, local drone imagery, and completed flightline products. Three colored input cards and arrows are placed directly under the title, before the flightline views and spectral graphs.

The routes remain distinct: NEON downloads/corrects/creates sensor-like products; supported local drone inputs use a separate local-image workflow; bulk analysis streams existing products for comparisons and summaries without a new download or correction. The shared outputs bar is a catalogue of workflow outputs, not a claim that the inputs are jointly processed or spatially fused. This follows README.md and docs/vignettes/bulk-analysis.md. The bottom ribbon is a package capability summary; the third route explicitly bypasses fresh image processing.

Rebuild with `python provenance/results-poster/2026-10-27/three_streams_revision/build_poster.py` using ReportLab and pypdf. Existing flightline images and the prior vector graph PDFs are reused; no scientific computations or graph changes occur. See ../visual_revision/README.md for graph source, units and display caveats, and ../flightline_revision/imagery_manifest.json for raw imagery provenance.

The flightline images are scaled proportionally to 28 inches wide, approximately 191 native pixels per printed inch; annotations and graphs remain vector content. Earlier poster PDFs are preserved.

Verification: one-page 36 x 48 inch dimensions, three stream names and explicit bulk bypass text, graph headings and caveats, text bounds and Ruff pass. Full-page Poppler render visually inspected: all three cards/arrows and outputs bar are visible; no overlapping labels, cropped imagery or clipped graph axes. Source/configuration hashes and output hash are recorded in manifest.json. No package behavior changed; package tests were not needed.
