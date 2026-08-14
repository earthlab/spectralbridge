# Packaged Scientific Data

This is the authoritative data directory installed with SpectralBridge. Runtime
code resolves these files through `spectralbridge.utils.get_package_data_path`;
do not replace those lookups with paths relative to a checkout.

| File | Meaning | Units / key contract | Primary consumer |
| --- | --- | --- | --- |
| `landsat_band_parameters.json` | Target sensor band centers and full widths at half maximum | Nanometers; each sensor has equal-length `wavelengths` and `fwhms` arrays | `standard_resample.py`, pipeline convolution, sensor panels |
| `hyperspectral_bands.json` | Reference hyperspectral wavelength axis used by sensor-panel visualization | Nanometers in the `bands` array | `sensor_panel_plots.py` |
| `brightness/landsat_to_micasense.json` | Percent brightness coefficients for the current Landsat-to-MicaSense system pair | Integer-like string band keys; percent values | `brightness_config.py` |
| `brightness/landsat_tm_etm_to_micasense.json` | Percent brightness coefficients for the TM/ETM+-specific comparison | Wavelength-aligned band order, not native Landsat band numbering | `brightness_config.py` |

The similarly named JSON files in repository-root `data/` are example/notebook
copies. Installed code uses this directory. Any scientific value change needs a
test, provenance note, and deliberate synchronization of example copies.

See `docs/reference/json-catalog.md` before editing a JSON value.

