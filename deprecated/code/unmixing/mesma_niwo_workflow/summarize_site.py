import pandas as pd

csv_path = "/data-store/iplant/home/shared/earthlab/macrosystems/january_26_processed_flight_lines/NIWO_b01/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance_polygons_merged_pixel_extraction.csv"

df = pd.read_csv(csv_path, low_memory=False)

print("\nAOP sites:")
print(df["aop_site"].value_counts())

print("\nImagery years:")
print(df["imagery_year"].value_counts())

print("\nCollection dates:")
print(df["collection_date"].dropna().head(20))

print("\nLongitude range:")
print(df["lon"].min(), df["lon"].max())

print("\nLatitude range:")
print(df["lat"].min(), df["lat"].max())
