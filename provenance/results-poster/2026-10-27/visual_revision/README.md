# Visual flightline and spectra poster

36 x 48 inch portrait PDF with a white background. This revision preserves the real visible/infrared flightline views, replaces text cards with spectral graphics and reduces the core-function explanation to a short four-step ribbon. Earlier posters remain intact.

## Rebuild

1. Run `build_graphs.py` with NumPy, pandas and Matplotlib.
2. Run `build_poster.py` with ReportLab and pypdf.

The graphs are embedded as vector PDFs. Flightline images retain their native 5351 x 1115 pixels (about 162 pixels per printed inch at full size). No raw-source reread, model fitting or package processing occurs.

## Scientific scope and sources

- Category curves and pointwise middle-50% shading come directly from the saved manuscript A_category_spectra.csv medians and quartiles, divided by 1,000 for display only. Physical reflectance scaling remains unresolved. Lines are split at saved-coordinate gaps. The graphs describe the separate polygon/year library, not samples extracted from the illustrated flightline. The poster states this distinction.
- The evergreen curve is the same saved category median, shown again to explain the transition from a detailed spectrum to band weighting.
- Gaussian weight shapes use the seven Landsat 8 OLI centers and FWHMs in src/spectralbridge/data/landsat_band_parameters.json, with sigma = FWHM / (2 sqrt(2 ln(2))), matching _build_sensor_srfs in pipelines/pipeline.py. They show the configured weight shapes at unit peak, not measured spectral response curves, output band values or independent calibration evidence. No convolution or fitted sensor relationship is computed for the poster.
- Gray excluded-region shading is an approximate display guide; actual curve breaks follow saved wavelength coordinates. Transparent IQR envelopes show pointwise observed spread, not confidence or probability regions. Repeated polygon/year observations are descriptive, not independent plant replicates.
- The two flightline views reuse the earlier source-audited assets and are explicitly not a correction-efficacy comparison. No species, health, temperature or field-fraction claims follow from their display colors.

manifest.json records source/output hashes and PDF checks. layout_boxes.json records external annotations. Graph PDFs are reproducible supporting assets. The earlier flightline imagery manifest retains raw source identity, selected wavelengths and display transformation.

## Verification

One-page 36 x 48 inch dimensions, required graph/function/caveat text and text bounds pass. Full-page Poppler rendering visually inspected: white background, complete flightline footprints, graph axes and legends, readable annotation hierarchy and no overlap or clipping. Scientific source files and previous posters remain unchanged. No package behavior changes; package tests are unnecessary for this artifact revision.
