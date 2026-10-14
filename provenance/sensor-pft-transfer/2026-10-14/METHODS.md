# Methods fixed before sensor results

The NEON primary statistic and null are unchanged: block-centered binary mean
coefficient beta; fixed label-independent pooled within-block spectral SD s;
T = beta * sqrt(q) / s, q = sum of squared block-centered labels. Max is max |T|;
integrated is sum w T^2. The synchronized Tippett/NPC combines max and integrated
probability ranks and calibrates the minimum against the joint permutation
ensemble. Labels move as whole polygon/year curves within exact history blocks.
This assumes conditional label exchangeability, not merely equal means under
arbitrarily different covariance distributions.

NEON weights are normalized trapezoidal wavelength weights over disconnected
supported segments; no atmospheric-gap bridges. OLI is a discrete seven-channel
instrument: primary weights are 1/7 per band. This measures average channel-wise
standardized separation rather than wavelength-area separation. FWHM proportions
are a secondary metric that emphasizes wider response supports; they do not
provide independent replicate wavelengths and do not allocate the large gaps
between bands to OLI. We do not use a trapezoidal line across multispectral centers.

RMS effect = sqrt(sum w (beta/s)^2), which removes the sample-size multiplier in
the test. Different sensor metrics make ratios descriptive representation-specific
separation ratios, not a universal information percentage. Within-band positive
multiplicative darkening leaves beta/s unchanged algebraically; verify the stored
transformation and compact aggregate numerics rather than equating it with new
spectral information. Do not alter reflectance scaling or brightness coefficients.

Band direction compares actual OLI beta/s with beta/s of a projection of the
same NEON polygon/year spectra onto packaged OLI Gaussian response profiles.
This latter diagnostic applies a linear operator after medians, whereas the
stored synthetic product was reduced before medians; equality is not assumed.
No physical MicaSense direction is tested while its mapping is unverified.
Pointwise bootstrap intervals are uncertainty aids; max envelopes remain null
localization tools, not effect confidence bands.

Paired cluster bootstrap and multiplicity choices are in DESIGN.md. The primary
estimand concerns sampled species/class mixtures. Spatial confounding, taxonomy,
nonrandom cover labels and missing metadata remain scientific limitations. No
novel-site/species classification or empirical satellite/drone validation is claimed.

## Statistic columns and uncertainty outputs

`sensor_contrasts.csv` reports the observed maximum and integrated statistics,
raw/adjusted component and NPC p-values, and `npc_statistic`: the minimum of the
two synchronized partial permutation probabilities (smaller is more extreme),
which is calibrated separately to obtain `p_npc`. It is not an uncorrected
minimum-p declaration. `band_retention.csv` includes signed OLI beta and beta/s,
projection direction and pointwise intervals; `neon_signed_contrasts.csv` records
the corresponding native NEON curve and pointwise intervals. MicaSense columns
are missing with an explicit blocked status.

`retention_summary.csv` additionally gives the median paired effect ratio over
the fixed eligible contrast set and its coupled-GlobalID bootstrap interval.
This is uncertainty conditional on these sites, classes, acquisition patterns
and selected contrasts, not a sample of independent ecological contrasts.
`contrast_ranks.csv` ranks effects separately within each cohort. Raw native
mean-curve cosines from the earlier audit are not numerically comparable to the
standardized beta/s cosines used in the current cross-site table.
