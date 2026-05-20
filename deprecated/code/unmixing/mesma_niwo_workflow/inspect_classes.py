import pandas as pd

csv_path = "/data-store/iplant/home/shared/earthlab/macrosystems/january_26_processed_flight_lines/NIWO_b01/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance_polygons_merged_pixel_extraction.csv"

df = pd.read_csv(csv_path, low_memory=False)

print(df["cover_category"].value_counts())

print("\n")

print(df["cover_subcategory"].value_counts())

print("\n")

print(df["combined_all_category_species"].value_counts().head(20))
