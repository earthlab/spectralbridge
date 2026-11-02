# Novice flightline poster revision

The new PDF preserves the earlier analytical poster and uses three views of the one full real flightline available locally. It does not imply three separate flights or correction improvement. All views have identical original orientation, footprint and native 5351 x 1115 image dimensions. The 33-inch image width yields approximately 162 native pixels per printed inch. Type and annotation lines are vector graphics.

Run `render_imagery.py` with NumPy, rasterio and Pillow, then `build_poster.py` with ReportLab and pypdf. Rendering reads six selected bands from the completed corrected raster, not the full 426-band cube. The source raster and prior analytical outputs are unchanged. It does not rerun corrections, fit models, access network data, or create a pixel table.

Channels are selected by nearest documented wavelength, not assumed indices. Exact wavelengths, original source/header hashes, channel percentiles, dimensions, grid, alpha support and display transformation are recorded in imagery_manifest.json. Finite negative pixels remain eligible. All colors are display-only per-channel 2nd-98th percentile stretches with gamma 0.8; these views are neither quantitative classification nor a comparison of correction efficacy. Transparent pixels indicate missing source support. No AI-generated imagery or synthetic terrain is used.

A road provides a visual reference. Marker B identifies the identical source coordinate in all three views. Statements about its apparent red/green appearance are visual descriptions, not an inferred plant class or health score. The one-flight scope, enhanced colors and channels are printed on the poster.

Verification: one-page 36 x 48 inch dimensions, extracted caveats and horizontal text bounds pass. Full-page Poppler preview visually inspected with no text clipping, overlap or image distortion; three-image footprint and orientation match. Source imagery retained at native resolution. No package behavior changed, so package tests were not needed.
