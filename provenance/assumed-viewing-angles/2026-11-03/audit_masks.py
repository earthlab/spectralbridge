"""Audit finite H5 numerical support against retained source alpha in polygons."""

from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, geometry_window

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    pol = gpd.read_file(
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    rows = []
    for name in ["gordon", "goldhill", "ruby"]:
        with rasterio.open(
            "/private/tmp/goldhill-radiometric-recovery-20261102/"
            + name
            + "_recovered_source_dn.tif"
        ) as s:
            candidates = pol.to_crs(s.crs)
            for a in candidates.itertuples():
                if a.geometry is None or a.geometry.is_empty:
                    continue
                try:
                    w = geometry_window(s, [a.geometry])
                except rasterio.errors.WindowError:
                    continue
                mask = geometry_mask(
                    [a.geometry],
                    out_shape=(int(w.height), int(w.width)),
                    transform=s.window_transform(w),
                    invert=True,
                )
                alpha = s.read(11, window=w)
                valid = np.isfinite(s.read(list(range(1, 11)), window=w)).all(0) & mask
                if valid.any():
                    rows.append(
                        dict(
                            flight=name,
                            GlobalID=a.GlobalID,
                            cover_category=a.cover_category,
                            finite_H5_memberships=int(valid.sum()),
                            alpha_zero_memberships=int((valid & (alpha == 0)).sum()),
                            alpha_positive_memberships=int(
                                (valid & np.isfinite(alpha) & (alpha > 0)).sum()
                            ),
                        )
                    )
    pd.DataFrame(rows).to_csv(HERE / "source_alpha_audit.csv", index=False)
    print(
        "Finite-H5 / source-alpha polygon audit saved; no file or alpha values changed."
    )


if __name__ == "__main__":
    main()
