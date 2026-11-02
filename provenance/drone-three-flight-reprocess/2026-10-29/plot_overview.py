"""Display-only geographic overview of the three independently checked outputs."""
import json
from pathlib import Path

import geopandas as gpd
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from rasterio.enums import Resampling
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
WORK = Path('/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1')
reports = json.loads((EVIDENCE / 'validation_summary.json').read_text())
assert len(reports) == 3 and all(r['maximum_displacement_pixels'] <= 1e-5 for r in reports.values())
polygons = gpd.read_file(REPO / 'Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg')
fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
for ax, name in zip(axes, ['AOP-GORDON-08-14-23-ExportPackage',
                          'AOP-GOLDHILL-08-14-23-ExportPackage', 'AOP-Ruby-08-14-23-ExportPackage']):
    record = reports[name]
    flight = Path(record['flight_dir'])
    with h5py.File(flight / (flight.name + '__working.h5')) as h:
        waves = next(iter(h.values()))['Reflectance/Metadata/Spectral_Data/Wavelength'][()]
    bands = [int(np.argmin(abs(waves - target))) + 1 for target in [650, 560, 475]]
    with rasterio.open(flight / (flight.name + '__corrected.img')) as src:
        factor = min(1., 700 / max(src.width, src.height))
        values = src.read(bands, out_shape=(3, max(1, int(src.height * factor)), max(1, int(src.width * factor))),
                          resampling=Resampling.nearest)
        rgb = np.moveaxis(values, 0, -1).astype('float64')
        valid = np.isfinite(rgb).all(axis=2)
        for channel in range(3):
            lo, hi = np.percentile(rgb[:, :, channel][valid], [2, 98])
            rgb[:, :, channel] = np.clip((rgb[:, :, channel] - lo) / max(hi - lo, 1e-12), 0, 1)
        rgb[~valid] = 1
        bounds = src.bounds
        ax.imshow(rgb, extent=[bounds.left, bounds.right, bounds.bottom, bounds.top], origin='upper')
        local = polygons.to_crs(src.crs)
        local = local.cx[bounds.left:bounds.right, bounds.bottom:bounds.top]
        local.boundary.plot(ax=ax, color='#ffbd47', linewidth=.65)
        ax.add_patch(Rectangle((bounds.left, bounds.bottom), bounds.right - bounds.left,
                               bounds.top - bounds.bottom, fill=False, edgecolor='#26873f', linewidth=1.5))
        ax.set_xlim(bounds.left, bounds.right)
        ax.set_ylim(bounds.bottom, bounds.top)
        ax.set_aspect('equal')
        ax.set_title(name.split('-')[1].title() + f"\n{record['records']:,} extracted records · source grid verified", fontsize=12)
        ax.set_xlabel('Easting (m), NAD83 / UTM 13N')
        ax.tick_params(labelsize=8)
        ax.ticklabel_format(useOffset=False, style='plain')
axes[0].set_ylabel('Northing (m)')
fig.suptitle('Gordon, Goldhill and Ruby — fully reprocessed\nResearcher polygons in gold; display contrast adjusted per flight. Scientific QA still requires review.', fontsize=14)
fig.savefig(EVIDENCE / 'three_flight_overview.png', dpi=180)
fig.savefig(EVIDENCE / 'three_flight_overview.pdf')
plt.close(fig)
print('Saved three-flight corrected-image overview')
