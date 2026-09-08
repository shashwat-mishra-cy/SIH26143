import polars as pl
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "output"
    / "cleaned"
    / "ais_final_trajectory.parquet"
)

OUTPUT_DIR = BASE_DIR / "output" / "quality"
OUTPUT_FILE = OUTPUT_DIR / "ais_quality_flagged.parquet"


# ============================================================
# THRESHOLDS
# ============================================================

# Movement state
STATIONARY_SPEED_KMH = 1.0

# Observation gap
LONG_GAP_SECONDS = 15 * 60       # 15 minutes

# Position discontinuity
MAX_REASONABLE_SPEED_KMH = 100.0

# Difference between calculated and reported speed
SPEED_MISMATCH_THRESHOLD_KMH = 50.0


# ============================================================
# LOAD
# ============================================================

print("Loading AIS trajectory data...")

df = pl.read_parquet(INPUT_FILE)

print(f"Loaded {df.height:,} records")


# ============================================================
# MOVEMENT STATE
# ============================================================

df = df.with_columns(

    pl.when(
        pl.col("calculated_speed_kmh")
        .fill_null(0)
        <= STATIONARY_SPEED_KMH
    )
    .then(pl.lit("stationary"))
    .otherwise(pl.lit("moving"))
    .alias("movement_state")
)


# ============================================================
# QUALITY FLAGS
# ============================================================

df = df.with_columns(

    # Large observation gap
    (
        pl.col("delta_seconds").fill_null(0)
        > LONG_GAP_SECONDS
    ).alias("is_long_gap"),

    # Physically implausible movement between consecutive points
    (
        (
            pl.col("calculated_speed_kmh")
            > MAX_REASONABLE_SPEED_KMH
        )
        &
        (
            pl.col("delta_seconds") > 0
        )
    )
    .fill_null(False)
    .alias("is_impossible_jump"),

    # Strong disagreement between trajectory-derived speed
    # and AIS-reported SOG
    (
        pl.col("speed_difference_kmh").abs()
        > SPEED_MISMATCH_THRESHOLD_KMH
    )
    .fill_null(False)
    .alias("is_speed_mismatch"),
)


# ============================================================
# QUALITY CLASSIFICATION
# ============================================================

df = df.with_columns(

    pl.when(
        pl.col("is_impossible_jump")
        & pl.col("is_speed_mismatch")
    )
    .then(pl.lit("impossible_jump_and_speed_mismatch"))

    .when(
        pl.col("is_impossible_jump")
    )
    .then(pl.lit("impossible_jump"))

    .when(
        pl.col("is_speed_mismatch")
    )
    .then(pl.lit("speed_mismatch"))

    .when(
        pl.col("is_long_gap")
    )
    .then(pl.lit("long_gap"))

    .otherwise(pl.lit("normal"))

    .alias("quality_flag")
)


# ============================================================
# QUALITY ISSUE SCORE
# ============================================================

# This score represents DATA QUALITY problems.
#
# It is NOT a vessel suspicion score.
#
# 0 = no detected quality issue
# 1 = long observation gap
# 2 = speed mismatch
# 3 = impossible jump
# 5 = impossible jump + speed mismatch

df = df.with_columns(

    (
        pl.col("is_long_gap").cast(pl.Int8) * 1
        +
        pl.col("is_speed_mismatch").cast(pl.Int8) * 2
        +
        pl.col("is_impossible_jump").cast(pl.Int8) * 3
    )
    .alias("quality_issue_score")
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df.write_parquet(OUTPUT_FILE)


print("\n" + "=" * 60)
print("QUALITY FLAGGING COMPLETE")
print("=" * 60)

print(f"Output: {OUTPUT_FILE}")


# ============================================================
# SUMMARY
# ============================================================

print("\nMovement state:")

movement_summary = (
    df
    .group_by("movement_state")
    .agg(
        pl.len().alias("records"),
        pl.col("mmsi").n_unique().alias("unique_vessels")
    )
    .sort("records", descending=True)
)

print(movement_summary)


print("\nObservation quality:")

quality_summary = (
    df
    .group_by("quality_flag")
    .agg(
        pl.len().alias("records"),
        pl.col("mmsi").n_unique().alias("unique_vessels")
    )
    .sort("records", descending=True)
)

print(quality_summary)


print("\nIndividual quality indicators:")

print(
    df.select(
        pl.col("is_long_gap").sum().alias("long_gap_records"),
        pl.col("is_impossible_jump").sum().alias("impossible_jump_records"),
        pl.col("is_speed_mismatch").sum().alias("speed_mismatch_records"),
    )
)