"""Check published comparisons and source immutability without source-image reads."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
P=Path(__file__).resolve().parent;R=P.parents[1]
for source in json.loads((P/'history_sources.json').read_text()):
 assert hashlib.sha256((R/source['path']).read_bytes()).hexdigest()==source['sha256'],source['path']
cost=json.loads((P/'compact_cost.json').read_text());assert (P/'ruby_compact_calibration.parquet').stat().st_size==cost['compact_bytes'];assert len(pd.read_parquet(P/'ruby_compact_calibration.parquet'))==3341
r=pd.read_csv(P/'compact_outer_results.csv');f=r[(r.targets==64)&(r.views==99)&(r.design=='spatial')];assert len(f)==600
np.testing.assert_allclose([f.ratio.median(),f.ratio.mean(),f.absolute_variance_ratio.median(),f.absolute_variance_ratio.mean()],[.83760086096,1.13186759828,.76619367751,1.15814463],rtol=1e-7)
u=pd.DataFrame(json.loads((P/'compact_uncertainty.json').read_text()));assert u.groupby('design').normalization_supported.sum().to_dict()==dict(full=40,nested_selected=30)
p=pd.read_csv(P/'polygon_common_support.csv');assert p.groupby('configuration').polygon_id.nunique().eq(86).all();assert p.groupby('configuration').pixels.sum().eq(22506).all()
assert len(list((P/'figures').glob('*.png')))==12
contract=json.loads((P/'compact_contract.json').read_text());assert hashlib.sha256((P/'ruby_compact_calibration.parquet').read_bytes()).hexdigest()==contract['packet_sha256']
assert json.loads((P/'compact_lossless_equivalence.json').read_text())['maximum_coefficient_difference']<7e-7
print('Verified historical report immutability, compact packet identity, common-support metrics, 80 uncertainty decisions, 86 polygons and 12 figures.')
