"""Read supplied endmember files in place; do not assume an index convention."""

from pathlib import Path
import hashlib
import json
import pickle
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
INPUT = Path("/Users/tuff/Downloads")


class StringArrayUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {
            ("numpy", "ndarray"): np.ndarray,
            ("numpy", "dtype"): np.dtype,
            ("numpy.core.multiarray", "_reconstruct"): np._core.multiarray._reconstruct,
            (
                "numpy._core.multiarray",
                "_reconstruct",
            ): np._core.multiarray._reconstruct,
        }
        if (module, name) not in allowed:
            raise ValueError(f"Unsupported serialized class: {module}.{name}")
        return allowed[module, name]


def labels(path):
    with path.open("rb") as stream:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version == (2, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError("Unsupported label array format")
        values = (
            StringArrayUnpickler(stream).load()
            if dtype.hasobject
            else np.load(path, allow_pickle=False)
        )
    if (
        not isinstance(values, np.ndarray)
        or values.shape != shape
        or values.ndim != 1
        or not all(isinstance(v, str) for v in values)
    ):
        raise ValueError("Expected one-dimensional string label array")
    return values.astype(str)


def main():
    paths = [
        INPUT / "library_oli_undarkened_10_12_26.npy",
        INPUT / "class_list_oli_undarkened_10_12_26.npy",
        INPUT / "selected_constrained_members.csv",
    ]
    x = np.load(paths[0], allow_pickle=False).T
    y = labels(paths[1])
    indices = pd.read_csv(paths[2]).iloc[:, 0].to_numpy()
    assert x.shape == (len(y), 7) and np.isfinite(x).all()
    assert indices.dtype.kind in "iu" and len(np.unique(indices)) == len(indices)
    source = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    p = pq.ParquetFile(source)
    bands = [n for n in p.schema_arrow.names if n.startswith("olioli_undarkened_b")]
    assert len(bands) == 7
    d = p.read(
        columns=bands + ["GlobalID", "cover_category", "flight_id", "imagery_year"]
    ).to_pandas()
    assert len(d) == len(x) and np.array_equal(d.cover_category.to_numpy(), y)
    scaled = d[bands].to_numpy() / 10000
    difference = float(np.max(np.abs(scaled - x)))
    assert np.allclose(scaled, x, rtol=2e-7, atol=1e-7)
    acquisition = d.flight_id.str.extract(r"_(\d{8})_")[0]
    assert acquisition.notna().all()
    actual_year = acquisition.str[:4].astype(int)
    hypotheses = {}
    for base in [0, 1]:
        ix = indices - base
        assert ix.min() >= 0 and ix.max() < len(x)
        hypotheses[str(base)] = {
            "category_counts": pd.Series(y[ix]).value_counts().to_dict(),
            "polygon_identities": int(d.iloc[ix].GlobalID.nunique()),
            "duplicate_selected_spectra": int(len(ix) - len(np.unique(x[ix], axis=0))),
        }
    result = {
        "status": "preflight passed; selected-index convention and selection provenance unconfirmed",
        "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "shape_observations_by_bands": list(x.shape),
        "category_counts": pd.Series(y).value_counts().to_dict(),
        "selected_indices": len(indices),
        "index_min": int(indices.min()),
        "index_max": int(indices.max()),
        "finite_spectra": int(np.isfinite(x).all(1).sum()),
        "negative_rows": int((x < 0).any(1).sum()),
        "source_parquet": str(source),
        "alignment": "All labels match in order; all seven scaled source columns match within recorded tolerance",
        "alignment_max_absolute_difference": difference,
        "scaling_relation": "supplied array approximately source stored values / 10000; this is numerical lineage, not physical unit validation",
        "polygon_identities": int(d.GlobalID.nunique()),
        "source_acquisition_year_counts": actual_year.value_counts()
        .sort_index()
        .to_dict(),
        "imagery_year_disagrees_with_source_year_rows": int(
            (actual_year != d.imagery_year).sum()
        ),
        "index_base_hypotheses": hypotheses,
        "selected_index_overlap_between_conventions": len(
            set(indices) & set(indices - 1)
        ),
        "interpretation": "Do not score one proposed selected library as definitive until index convention is known. Non-selected pixels are not independent test plants. Selection using full library also prevents an honest selection-blind holdout claim.",
    }
    (OUT / "input_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
