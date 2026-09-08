import polars as pl
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "quality"
    / "ais_quality_flagged.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "quality"

OUTPUT_FILE = (
    OUTPUT_DIR
    / "ais_quality_events.parquet"
)


# ============================================================
# LOAD
# ============================================================

print("Loading quality-flagged AIS data...")

df = pl.read_parquet(INPUT_FILE)

print(f"Loaded {df.height:,} records")


# ============================================================
# SELECT QUALITY EVENTS
# ============================================================

events = (
    df
    .filter(
        pl.col("quality_flag") != "normal"
    )
    .select(
        [
            "mmsi",
            "base_date_time",
            "prev_timestamp",

            "latitude",
            "longitude",

            "prev_latitude",
            "prev_longitude",

            "delta_seconds",
            "distance_km",

            "calculated_speed_kmh",
            "sog_kmh",
            "speed_difference_kmh",

            "movement_state",

            "is_long_gap",
            "is_impossible_jump",
            "is_speed_mismatch",

            "quality_flag",
            "quality_issue_score",
        ]
    )
    .sort(
        [
            "mmsi",
            "base_date_time"
        ]
    )
)


# ============================================================
# EVENT ID
# ============================================================

events = events.with_columns(

    pl.int_range(
        0,
        pl.len()
    )
    .alias("quality_event_id")
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

events.write_parquet(OUTPUT_FILE)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 60)
print("QUALITY EVENTS CREATED")
print("=" * 60)

print(f"Total events: {events.height:,}")

print(f"Output: {OUTPUT_FILE}")


print("\nEvents by type:")

summary = (
    events
    .group_by("quality_flag")
    .agg(
        pl.len().alias("events"),
        pl.col("mmsi").n_unique().alias("unique_vessels")
    )
    .sort("events", descending=True)
)

print(summary)


print("\nTop vessels by quality events:")

vessel_summary = (
    events
    .group_by("mmsi")
    .agg(
        pl.len().alias("quality_events"),
        pl.max("quality_issue_score")
        .alias("max_quality_score")
    )
    .sort(
        "quality_events",
        descending=True
    )
    .head(20)
)

print(vessel_summary)