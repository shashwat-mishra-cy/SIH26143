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

EVENT_FILE = (
    BASE_DIR
    / "output"
    / "quality"
    / "ais_quality_events.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "quality"


# ============================================================
# LOAD
# ============================================================

df = pl.read_parquet(INPUT_FILE)
events = pl.read_parquet(EVENT_FILE)


# ============================================================
# BASIC DATASET INFORMATION
# ============================================================

total_records = df.height
total_vessels = df["mmsi"].n_unique()


# ============================================================
# MOVEMENT
# ============================================================

stationary_records = (
    df
    .filter(pl.col("movement_state") == "stationary")
    .height
)

moving_records = (
    df
    .filter(pl.col("movement_state") == "moving")
    .height
)


# ============================================================
# QUALITY
# ============================================================

long_gaps = (
    df
    .filter(pl.col("is_long_gap"))
    .height
)

impossible_jumps = (
    df
    .filter(pl.col("is_impossible_jump"))
    .height
)

speed_mismatches = (
    df
    .filter(pl.col("is_speed_mismatch"))
    .height
)


# ============================================================
# SEVERE JUMPS
# ============================================================

severe_200 = (
    df
    .filter(
        pl.col("calculated_speed_kmh") > 200
    )
    .height
)

severe_1000 = (
    df
    .filter(
        pl.col("calculated_speed_kmh") > 1000
    )
    .height
)

extreme_100000 = (
    df
    .filter(
        pl.col("calculated_speed_kmh") > 100000
    )
    .height
)


# ============================================================
# TOP PROBLEMATIC VESSELS
# ============================================================

top_vessels = (
    events
    .group_by("mmsi")
    .agg(
        pl.len().alias("quality_events"),

        pl.col("is_impossible_jump")
        .sum()
        .alias("impossible_jumps"),

        pl.col("is_speed_mismatch")
        .sum()
        .alias("speed_mismatches"),

        pl.col("is_long_gap")
        .sum()
        .alias("long_gaps"),
    )
    .sort(
        "quality_events",
        descending=True
    )
    .head(20)
)


# ============================================================
# WRITE REPORT
# ============================================================

report_file = (
    OUTPUT_DIR
    / "ais_quality_report.txt"
)

with open(report_file, "w", encoding="utf-8") as f:

    f.write("AIS DATA QUALITY REPORT\n")
    f.write("=" * 70 + "\n\n")

    f.write("DATASET\n")
    f.write("-" * 70 + "\n")
    f.write(f"Total records: {total_records:,}\n")
    f.write(f"Unique vessels: {total_vessels:,}\n\n")

    f.write("MOVEMENT STATE\n")
    f.write("-" * 70 + "\n")
    f.write(f"Stationary records: {stationary_records:,}\n")
    f.write(f"Moving records: {moving_records:,}\n\n")

    f.write("QUALITY INDICATORS\n")
    f.write("-" * 70 + "\n")
    f.write(f"Long gaps: {long_gaps:,}\n")
    f.write(f"Impossible jumps: {impossible_jumps:,}\n")
    f.write(f"Speed mismatches: {speed_mismatches:,}\n\n")

    f.write("IMPOSSIBLE JUMP SEVERITY\n")
    f.write("-" * 70 + "\n")
    f.write(f">200 km/h: {severe_200:,}\n")
    f.write(f">1000 km/h: {severe_1000:,}\n")
    f.write(f">100000 km/h: {extreme_100000:,}\n\n")

    f.write("TOP VESSELS BY QUALITY EVENTS\n")
    f.write("-" * 70 + "\n")

    f.write(
        top_vessels
        .to_pandas()
        .to_string(index=False)
    )

    f.write("\n")


print("=" * 70)
print("AIS QUALITY REPORT GENERATED")
print("=" * 70)
print(report_file)