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
pip install spectralbridge
```

`rioxarray` / `xarray` remain useful optional analysis companions for reading
ENVI outputs in notebooks, but they are not declared as direct runtime package
dependencies.

## Setup (conda)
```bash
conda create -n spectralbridge python=3.11 -y
conda activate spectralbridge
pip install -U pip
pip install spectralbridge
```
