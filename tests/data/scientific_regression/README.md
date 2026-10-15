# Frozen derived scientific regression fixtures

These tiny JSON fixtures contain derived numerical evidence, not redistributed
source imagery or full pixel libraries. Origin/product, original file SHA256,
selection, units and band order are embedded. Real Landsat data are public USGS
Collection 2 observations; the retained arrays are six matched derived records
from the documented R10C pilot. They are not an independent flight or a new
validation experiment. No raw raster, credentials or network access is required.

`landsat_derived.json`: six equally spaced row indices from the canonical
pixel_metrics table, original-registration undarkened synthetic OLI versus actual
Landsat SR, seven ordered channels, frozen numerical summaries.

`pft_transfer.json`: 21 canonical inferred-PFT contrast/cohort records, not 21
independent experiments. The fixture guards the evidence record and website
summary. Solver correctness is separately tested with analytic synthetic data.

Do not refresh expected results automatically on failures. A changed scientific
result requires explicit scientific review and documented source reconciliation.

`learning_predictions.json` retains ten actual held-out PFT plant-fold logistic
predictions (two per label, including errors where available), with original output hash and context. Its independent
scikit-learn metric values protect classification metric regression; this subset
is not promoted to a new independent validation dataset or the full-fold score.
