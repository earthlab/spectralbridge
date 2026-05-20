import pandas as pd

csv_path = "/data-store/iplant/home/shared/earthlab/macrosystems/january_26_processed_flight_lines/NIWO_b01/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance_polygons_merged_pixel_extraction.csv"

df = pd.read_csv(csv_path, low_memory=False)

bands = [
    "olioli_b001_wl0443nm",
    "olioli_b002_wl0482nm",
    "olioli_b003_wl0561nm",
    "olioli_b004_wl0655nm",
    "olioli_b005_wl0865nm",
    "olioli_b006_wl1609nm",
    "olioli_b007_wl2201nm"
]

for band in bands:
    vals = df[band]

    print("\n", band)
    print("min:", vals.min())
    print("max:", vals.max())

