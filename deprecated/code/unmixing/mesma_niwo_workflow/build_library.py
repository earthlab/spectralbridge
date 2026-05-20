import pandas as pd
import numpy as np

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

# keep only needed columns
keep_cols = ["cover_category"] + bands

df = df[keep_cols]

# replace obvious no-data
df = df.replace(-9999, np.nan)

# remove rows with missing values
df = df.dropna()

# remove rows with negative reflectance
for band in bands:
    df = df[df[band] >= 0]

# scale reflectance
# TRYING division by 10000 first
for band in bands:
    df[band] = df[band] / 10000.0

print("Rows remaining:", len(df))

print("\nClass counts:")
print(df["cover_category"].value_counts())

print("\nBand ranges after scaling:")
for band in bands:
    print(
        band,
        "min=", df[band].min(),
        "max=", df[band].max()
    )

# create MESMA inputs

class_list = df["cover_category"].values

library = df[bands].to_numpy().T

print("\nLibrary shape:")
print(library.shape)

print("\nFirst few class labels:")
print(class_list[:10])

np.save("library_oli.npy", library)
np.save("class_list_oli.npy", class_list)

print("\nSaved:")
print("library_oli.npy")
print("class_list_oli.npy")
