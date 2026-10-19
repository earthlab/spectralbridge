# Environment

| Component | Known-good |
|---|---|
| Python   | 3.10–3.12 |
| OS       | macOS 13+, Ubuntu 22.04+ |
| Core libs| numpy, pandas, pyarrow, h5py, rasterio, geopandas, ray, duckdb, spectral |

## Setup (venv)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e .
```

`rioxarray` / `xarray` remain useful optional analysis companions for reading
ENVI outputs in notebooks, but they are not declared as direct runtime package
dependencies.

## Setup (conda)
```bash
conda create -n spectralbridge python=3.11 -y
conda activate spectralbridge
pip install -U pip
pip install -e .
```

The source-install commands assume you have cloned
[`earthlab/spectralbridge`](https://github.com/earthlab/spectralbridge) and changed
into its directory. The distribution name is `earthlab-spectralbridge`, but no
PyPI project was exposed at that name in the 19 October 2026 audit. See the
[beginner path](getting-started.md) for setup and a tiny offline example.
