
from pathlib import Path

import numpy as np
import pytest

from spectralbridge.file_types import NEONReflectanceENVIFile, SpectralDataParquetFile
from spectralbridge.polygon_extraction import _process_single_raster, process_raster_in_chunks
from tests.conftest import MODE, require_mode

pytestmark = require_mode("full")

if MODE != "full":
    pytest.skip("CSCAL_TEST_MODE!='full'", allow_module_level=True)

class DummyDataFile:
    def __init__(self, path: Path):
        self.path = path


class _RecordingParquetWriter:
    def __init__(self, path, schema):
        self.path = path
        self.schema = schema
        self.tables = []

    def write_table(self, table):
        self.tables.append(table)

    def close(self):
        return None

def test_process_single_raster_skips_existing_output(tmp_path, monkeypatch):
    raster_folder = tmp_path / "raster" / "nested"
    raster_folder.mkdir(parents=True)
    raster_file = NEONReflectanceENVIFile.from_components(
        domain="D01",
        site="ABCD",
        tile="L001-1",
        date="20220101",
        time="120000",
        folder=raster_folder,
    )
    spectral_file = SpectralDataParquetFile.from_raster_file(raster_file)
    spectral_file.path.write_text("existing")

    def fail(*args, **kwargs):  # pragma: no cover - should not run
        raise AssertionError("Extraction should have been skipped")

    monkeypatch.setattr("spectralbridge.polygon_extraction.process_raster_in_chunks", fail)

    _process_single_raster(raster_file, polygon_path=None)

def test_process_raster_in_chunks_skips_when_output_exists(tmp_path, monkeypatch):
    raster_path = tmp_path / "dummy.img"
    output_path = tmp_path / "out.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("existing")

    class FailRasterioModule:
        @staticmethod
        def open(*args, **kwargs):  # pragma: no cover - should not run
            raise AssertionError("Raster should not be opened when skipping")

    monkeypatch.setattr(
        "spectralbridge.polygon_extraction.require_rasterio",
        lambda: FailRasterioModule(),
    )

    process_raster_in_chunks(
        DummyDataFile(raster_path),
        polygon_path=None,
        output_parquet_file=DummyDataFile(output_path),
    )

def test_process_raster_in_chunks_overwrite_removes_existing_output(tmp_path, monkeypatch):
    raster_path = tmp_path / "dummy.img"
    output_path = tmp_path / "out.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("existing")

    class ExplodingDataset:
        def __enter__(self):
            raise RuntimeError("stop")

        def __exit__(self, exc_type, exc, tb):
            return False

    class ExplodingRasterioModule:
        @staticmethod
        def open(*args, **kwargs):
            return ExplodingDataset()

    monkeypatch.setattr(
        "spectralbridge.polygon_extraction.require_rasterio",
        lambda: ExplodingRasterioModule(),
    )

    with pytest.raises(RuntimeError):
        process_raster_in_chunks(
            DummyDataFile(raster_path),
            polygon_path=None,
            output_parquet_file=DummyDataFile(output_path),
            overwrite=True,
        )

    assert not output_path.exists()


def test_process_raster_in_chunks_streams_multiple_windows(tmp_path, monkeypatch):
    raster_path = tmp_path / "dummy.img"
    output_path = tmp_path / "out.parquet"
    raster_path.write_bytes(b"img")

    class FakeDataset:
        count = 2
        height = 5
        width = 4
        crs = None
        transform = object()

        def __init__(self):
            self.windows = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, window):
            self.windows.append(window)
            (row_start, row_end), (_col_start, col_end) = window
            rows = row_end - row_start
            cols = col_end
            return np.ones((self.count, rows, cols), dtype=np.float32)

    fake_dataset = FakeDataset()

    class FakeRasterioModule:
        @staticmethod
        def open(*args, **kwargs):
            return fake_dataset

    writes = []

    class FakeParquetModule:
        def ParquetWriter(self, path, schema):
            writer = _RecordingParquetWriter(path, schema)
            writes.append(writer)
            return writer

    class FakeArrowTable:
        def __init__(self, dataframe):
            self.dataframe = dataframe
            self.schema = tuple(dataframe.columns)

    class FakeArrowModule:
        class Table:
            @staticmethod
            def from_pandas(dataframe, preserve_index=False):
                return FakeArrowTable(dataframe)

    class DummyTqdm:
        def __init__(self, *args, **kwargs):
            self.updates = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def update(self, n):
            self.updates += n

    monkeypatch.setattr("spectralbridge.polygon_extraction.require_rasterio", lambda: FakeRasterioModule())
    monkeypatch.setattr("spectralbridge.polygon_extraction._require_pyarrow_parquet", lambda: FakeParquetModule())
    monkeypatch.setattr("spectralbridge.polygon_extraction._require_pyarrow", lambda: FakeArrowModule())
    monkeypatch.setattr("spectralbridge.polygon_extraction.ensure_coord_columns", lambda df, **kwargs: df)
    monkeypatch.setattr(
        "spectralbridge.polygon_extraction.sort_and_rename_spectral_columns",
        lambda df, **kwargs: df,
    )
    monkeypatch.setattr("spectralbridge.polygon_extraction.tqdm", DummyTqdm)

    process_raster_in_chunks(
        DummyDataFile(raster_path),
        polygon_path=None,
        output_parquet_file=DummyDataFile(output_path),
        chunk_size=6,
    )

    assert len(fake_dataset.windows) == 4
    assert fake_dataset.windows == [
        ((0, 2), (0, 4)),
        ((1, 4), (0, 4)),
        ((3, 5), (0, 4)),
        ((4, 5), (0, 4)),
    ]
    assert len(writes) == 1
    assert len(writes[0].tables) == 4
