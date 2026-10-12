# Why sensors see the same landscape differently

SpectralBridge helps researchers prepare and compare observations of reflected
light. Different sensors observe the same landscape differently. A **common
framework, with sensor-specific treatment**, makes those differences inspectable;
it does not make the sensors interchangeable.

## Reflectance: how a surface returns light

Reflectance describes how much incoming light a surface reflects under stated
measurement conditions. A value of 0.2 represents 20% in a simple fraction-based
example. An image may store scaled integers rather than fractions: the file's
units, scaling and missing-value metadata must be interpreted before comparison.
Illumination, view direction and the mix of surfaces in a pixel also matter.
Reflectance is not simply the brightness of a displayed photograph.

## Bands: which light a sensor records

A **spectral band** measures a range of wavelengths, like a channel sensitive to
part of the spectrum. Wavelength is often recorded in nanometres (nm).
A hyperspectral instrument records many closely spaced bands; a multispectral
instrument records fewer, broader bands. A band's **spectral response function** (SRF) describes
how strongly it responds to each wavelength within its range. Two bands called
“red” can therefore return different values for the same surface.

## Three observing systems, three roles

| System | What it contributes | What comparison must account for |
| --- | --- | --- |
| NEON airborne imaging spectroscopy | Detailed spectra plus acquisition/geometry metadata over flightlines | Many bands, data scaling, terrain and directional effects |
| Drone instruments such as MicaSense | Fine-detail, local observations collected for a study | Camera preparation, wavelengths, available ancillary data and acquisition conditions |
| Landsat satellites | Repeated observations over wider areas and larger ground footprints | Actual satellite observations differ from configured Landsat-like representations of airborne data |

NEON is the National Ecological Observatory Network. A **flightline** is an
observation acquired along one aircraft pass. These systems can support the same
study while retaining different measurement meanings.

## Geometry: where the light and sensor were

Slopes and sun/sensor directions change how reflected light is observed.
**Topographic correction** models terrain-related illumination effects;
**BRDF correction** models dependence on illumination and viewing directions.
BRDF means bidirectional reflectance distribution function. SpectralBridge uses
configured methods and records their outputs and diagnostics. Correction is a
modeling step with assumptions, not proof that all acquisition effects disappear.
[Technical methods and provenance](../brdf_topo_algorithm.md) give the equations
and source attribution, including the SCS+C topographic model.

## Spatial support: what ground area a value represents

A **pixel** summarizes a ground footprint, potentially mixing plants, soil,
shadows and other surfaces. **Spatial support** is the area and sampling process
represented by a measurement. A small drone pixel and a larger satellite pixel
can describe different mixtures even when their spectral bands are similar.
Spectral weighting does not align pixels or change their footprints. Spatial
alignment, aggregation, masking, dates and reference observations remain
scientifically consequential choices.

## What SpectralBridge changes

The NEON route exports observations, applies configured geometry corrections,
and weights detailed spectra into configured sensor-like band spaces. Those
weights must be interpreted through their recorded definitions and provenance;
packaged band centers/widths are not automatically measured response curves.
Separately recorded brightness or bandpass adjustments change the numerical
representation and require their own justification.

The drone route prepares supported local inputs, retains its native corrected
products and can explicitly apply reviewed affine coefficients. The bulk route
analyzes completed products and reports how relationships depend on flightlines,
sites and weighting. [Choose a workflow](../vignettes/index.md) from your inputs.

## What it does not establish

A Landsat-like representation derived from NEON is not an independently measured
Landsat observation. A successful run, complete output set or favorable internal
QA does not establish agreement with another sensor. The package does not provide
a universal drone-to-Landsat conversion or eliminate spatial-support differences.

Read [the evidence hierarchy](../validation/evidence-hierarchy.md), then try the
[small offline example](../getting-started.md). Advanced readers can continue to
[correction and weighting detail](why-calibration.md).

## File formats and method names you will meet next

**ENVI** stores a raster in an image file plus a text header describing shape,
bands, units and other metadata. **Parquet** stores tables by column for analysis.
Neither format, on its own, certifies a measurement's scientific validity.

**SCS+C** means sun-canopy-sensor plus C: the named topographic model used in the
configured correction route. **Bandpass adjustment** accounts for differences
between bands' wavelength responses under a stated method and context; its
transferability still requires evidence. The [technical methods](../brdf_topo_algorithm.md)
and [target-band guide](../vignettes/sensor-harmonization.md) explain the equations
and assumptions after these introductory concepts.
