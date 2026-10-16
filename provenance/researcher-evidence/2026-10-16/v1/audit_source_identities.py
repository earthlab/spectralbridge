"""Cross-check raw metadata identities against the analysis, without spectral copies."""

from pathlib import Path
import json
import pandas as pd
import pyarrow.parquet as pq

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]


def main():
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    f = (
        pq.read_table(source, columns=["GlobalID", "cover_category"])
        .to_pandas()
        .drop_duplicates()
    )
    assert not f.GlobalID.isna().any()
    assert f.groupby("GlobalID").cover_category.nunique().max() == 1
    old = pd.read_csv(
        REPO
        / "provenance/researcher-pft-information/2026-10-15/v1/tables/observation_index.csv"
    )
    assert set(f.GlobalID) == set(old.GlobalID)
    source_labels = f.set_index("GlobalID").cover_category
    expected = old.drop_duplicates("GlobalID").set_index("GlobalID").cover_category
    assert source_labels.reindex(expected.index).equals(expected)
    record = {
        "status": "passed",
        "source_GlobalIDs": f.GlobalID.nunique(),
        "matches_all_analytical_GlobalIDs": True,
        "source_category_conflicts": 0,
        "all_analysis_labels_equal_source_labels": True,
    }
    (BASE / "source_identity_validation.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(record)


if __name__ == "__main__":
    main()
