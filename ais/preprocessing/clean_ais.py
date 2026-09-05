import polars as pl
from pathlib import Path


# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "ais-2025-01-01.csv"

OUTPUT_FILE = (
    BASE_DIR
    / "output"
    / "cleaned"
    / "ais_cleaned.parquet"
)


# ==================================================
# READ DATA
# ==================================================

print("Reading AIS dataset...")

df = pl.read_csv(
    INPUT_FILE,
    infer_schema_length=10000
)

print("Original records:", df.height)


# ==================================================
# DATA TYPES
# ==================================================

df = df.with_columns([
    pl.col("mmsi").cast(pl.String),

    pl.col("base_date_time").str.to_datetime(),

    pl.col("longitude").cast(pl.Float64, strict=False),
    pl.col("latitude").cast(pl.Float64, strict=False),
    pl.col("sog").cast(pl.Float64, strict=False),
    pl.col("cog").cast(pl.Float64, strict=False),
    pl.col("heading").cast(pl.Float64, strict=False),

    pl.col("vessel_type").cast(pl.Int64, strict=False),
    pl.col("status").cast(pl.Int64, strict=False),

    pl.col("length").cast(pl.Float64, strict=False),
    pl.col("width").cast(pl.Float64, strict=False),
    pl.col("draft").cast(pl.Float64, strict=False),

    pl.col("cargo").cast(pl.Int64, strict=False)
])


# ==================================================
# BASIC VALIDATION
# ==================================================

print("\n========== BASIC VALIDATION ==========")

print("Missing MMSI:",
      df["mmsi"].null_count())

print("Missing timestamp:",
      df["base_date_time"].null_count())

print("Missing latitude:",
      df["latitude"].null_count())

print("Missing longitude:",
      df["longitude"].null_count())


# ==================================================
# COORDINATE VALIDATION
# ==================================================

invalid_coordinates = (
    (pl.col("latitude") < -90) |
    (pl.col("latitude") > 90) |
    (pl.col("longitude") < -180) |
    (pl.col("longitude") > 180)
)

print(
    "Invalid coordinates:",
    df.filter(invalid_coordinates).height
)


# ==================================================
# SOG / COG VALIDATION
# ==================================================

invalid_sog = (
    (pl.col("sog") < 0) |
    (pl.col("sog") > 102.2)
)

invalid_cog = (
    (pl.col("cog") < 0) |
    (pl.col("cog") >= 360)
)

print(
    "Invalid SOG:",
    df.filter(invalid_sog).height
)

print(
    "Invalid COG:",
    df.filter(invalid_cog).height
)


# ==================================================
# REMOVE RECORDS WITH ESSENTIAL DATA MISSING
# ==================================================

df = df.filter(
    pl.col("mmsi").is_not_null() &
    pl.col("base_date_time").is_not_null() &
    pl.col("latitude").is_not_null() &
    pl.col("longitude").is_not_null()
)


# ==================================================
# REMOVE INVALID COORDINATES
# ==================================================

df = df.filter(
    (pl.col("latitude") >= -90) &
    (pl.col("latitude") <= 90) &
    (pl.col("longitude") >= -180) &
    (pl.col("longitude") <= 180)
)


# ==================================================
# REMOVE EXACT DUPLICATES
# ==================================================

before = df.height

df = df.unique()

after = df.height

print("\n========== DUPLICATES ==========")

print("Before:", before)
print("After:", after)
print("Removed:", before - after)


# ==================================================
# RECORD VALIDITY
# ==================================================

df = df.with_columns(
    pl.lit(True).alias("record_valid")
)


# ==================================================
# FINAL STATISTICS
# ==================================================

print("\n========== FINAL DATASET ==========")

print("Final records:", df.height)

print(
    "Unique vessels:",
    df["mmsi"].n_unique()
)

print(
    "Earliest timestamp:",
    df["base_date_time"].min()
)

print(
    "Latest timestamp:",
    df["base_date_time"].max()
)


# ==================================================
# SAVE
# ==================================================

df.write_parquet(
    OUTPUT_FILE,
    compression="zstd"
)

print("\nCleaned dataset saved:")
print(OUTPUT_FILE)