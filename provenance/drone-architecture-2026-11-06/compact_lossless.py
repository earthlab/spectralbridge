"""Verify compact-packet equivalence to full retained photo observations."""
from pathlib import Path
import json,time
import numpy as np,pandas as pd
from spectralbridge.drone_original import fit_target_amplitudes
P=Path(__file__).resolve().parent;R=P.parents[1];start=time.monotonic();d=pd.read_parquet(P/'ruby_compact_calibration.parquet');d=d[d.quality_supported];old=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/brdf_models.json').read_text());rows=[]
for nm,a in d.groupby('wavelength_nm'):
 counts=a.groupby('target_id').size();a=a[a.target_id.isin(counts[counts>=3].index)];X=np.c_[np.ones(len(a)),a.ross,a.li];fit=fit_target_amplitudes(X,a.observed_fraction.to_numpy(),a.target_id.to_numpy());reference=next(v['coefficients'] for v in old if v['wavelength_nm']==nm and v['model']=='multiplicative_target_amplitudes');rows.append(dict(wavelength_nm=float(nm),observations=len(a),maximum_coefficient_difference=float(np.max(abs(fit['beta']-reference)))))
(P/'compact_lossless_equivalence.json').write_text(json.dumps(dict(results=rows,read_and_ten_band_fit_seconds=time.monotonic()-start,maximum_coefficient_difference=max(r['maximum_coefficient_difference'] for r in rows),scope='Same observations and model as P184; equivalence does not validate physical calibration or a new mosaic'),indent=2)+'\n');print(rows)
