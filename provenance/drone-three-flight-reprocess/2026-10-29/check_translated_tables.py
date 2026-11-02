"""Bounded full-value checks and native/translated extraction identity checks."""
from collections import OrderedDict
import json
from pathlib import Path
import re

import duckdb
import numpy as np
import pyarrow.parquet as pq
import rasterio
from rasterio.windows import Window

EVIDENCE = Path(__file__).resolve().parent
WORK = Path('/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1')
records = []
connection = duckdb.connect()
connection.execute("SET memory_limit='512MB'")
connection.execute("SET threads=1")
connection.execute("SET preserve_insertion_order=false")
for output in sorted((WORK / 'flight_products').iterdir()):
    result_path = output / 'pipeline_result.json'
    assert result_path.exists(), f'Pipeline has not completed: {output}'
    audit = json.loads(result_path.read_text())['qa_summary']['files'][0]
    flight = Path(audit['flight_dir'])
    native = flight / (flight.name + '__polygons.parquet')
    for product in audit['translation_products']:
        raster_path = Path(product['output_img'])
        table = raster_path.with_name(raster_path.stem + '__polygons.parquet')
        fields = pq.read_schema(table).names
        bands = sorted((int(match.group(1)), name) for name in fields
                       if (match := re.search(r'_b(\d+)_wl', name)))
        columns = ['row', 'col', 'x', 'y', *[name for _, name in bands]]
        identity = 'row, col, "GlobalID", cover_category'
        query = f'''SELECT count(*) FROM (
            (SELECT {identity} FROM read_parquet(?) EXCEPT ALL SELECT {identity} FROM read_parquet(?))
            UNION ALL
            (SELECT {identity} FROM read_parquet(?) EXCEPT ALL SELECT {identity} FROM read_parquet(?)))'''
        identity_differences = connection.execute(query, [str(table), str(native), str(native), str(table)]).fetchone()[0]
        assert identity_differences == 0, f'Translated extraction is incomplete or labels differ: {table}'
        row_count = values_checked = value_mismatches = coordinate_mismatches = 0
        cache = OrderedDict()
        with rasterio.open(raster_path) as raster:
            assert len(bands) == raster.count and [i for i, _ in bands] == list(range(1, raster.count + 1))
            for batch in pq.ParquetFile(table).iter_batches(batch_size=4096, columns=columns):
                data = batch.to_pydict()
                rows = np.asarray(data['row'], dtype='int64')
                cols = np.asarray(data['col'], dtype='int64')
                assert np.all((rows >= 0) & (rows < raster.height) & (cols >= 0) & (cols < raster.width))
                expected = np.empty((len(rows), raster.count), dtype='float32')
                for row in np.unique(rows):
                    if int(row) not in cache:
                        cache[int(row)] = raster.read(window=Window(0, int(row), raster.width, 1))[:, 0, :]
                        if len(cache) > 128:
                            cache.popitem(last=False)
                    selected = np.flatnonzero(rows == row)
                    expected[selected] = cache[int(row)][:, cols[selected]].T
                actual = np.column_stack([data[name] for _, name in bands])
                value_mismatches += int(np.count_nonzero(~((actual == expected) | (np.isnan(actual) & np.isnan(expected)))))
                xs, ys = rasterio.transform.xy(raster.transform, rows, cols, offset='center')
                coordinate_mismatches += int(np.count_nonzero(~np.isclose(xs, data['x'], rtol=0, atol=1e-7)))
                coordinate_mismatches += int(np.count_nonzero(~np.isclose(ys, data['y'], rtol=0, atol=1e-7)))
                row_count += len(rows)
                values_checked += actual.size
        assert not value_mismatches and not coordinate_mismatches, table
        records.append({'flight': flight.name, 'sensor': product['target_sensor'], 'rows': row_count,
                        'values_checked': values_checked, 'value_mismatches': value_mismatches,
                        'coordinate_mismatches': coordinate_mismatches, 'native_identity_differences': identity_differences})
        print('Translated table verified:', flight.name, product['target_sensor'], row_count, flush=True)
        (EVIDENCE / 'translated_table_checks.json').write_text(json.dumps(records, indent=2) + '\n')
assert len(records) == 12
connection.close()
