import pandas as pd

csv_path = "/data-store/iplant/home/shared/earthlab/macrosystems/january_26_processed_flight_lines/NIWO_b01/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance_polygons_merged_pixel_extraction.csv"

df = pd.read_csv(csv_path)

print("Columns:")
print(df.columns.tolist())

print("\nFirst 5 rows:")
print(df.head())

print("\nShape:")
print(df.shape)
