"""Execute the Parquet guide against a small current-style wide table."""
from pathlib import Path
import re

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def test_parquet_guide_queries_wide_columns_without_losing_negative_values(tmp_path, monkeypatch):
    guide = Path(__file__).resolve().parents[1] / "docs/usage/parquet.md"
    blocks = re.findall(r"```python\n(.*?)```", guide.read_text(), re.DOTALL)
    assert len(blocks) == 2
    monkeypatch.chdir(tmp_path)
    pq.write_table(pa.table({
        "pixel_id": [0, 1, 2],
        "corr_b001_wl0382nm": [-2.0, 4.0, None],
    }), "flight_merged_pixel_extraction.parquet")
    namespace = {}
    for block in blocks:
        exec(compile(block, str(guide), "exec"), namespace)
    result = namespace["relation"].aggregate(
        f'count(*) AS pixels, avg({namespace["quoted_band"]}) AS mean_reflectance'
    ).fetchone()
    assert result == (3, 1.0)
    pq.write_table(pa.table({"different_grid_b001_wl0385nm": [1.0]}),
                   "flight_merged_pixel_extraction.parquet")
    exec(compile(blocks[0], str(guide), "exec"), namespace)
    with pytest.raises(ValueError, match="Band not in supplied schema"):
        exec(compile(blocks[1], str(guide), "exec"), namespace)
