import polars as pl
from pathlib import Path
import math

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "output" / "cleaned" / "ais_trajectory.parquet"

OUTPUT_FILE = BASE_DIR / "output" / "cleaned" / "ais_final.parquet"

AUDIT_FILE = BASE_DIR / "output" / "cleaned" / "duplicate_resolution_audit.parquet"


# ============================================================
# HAVERSINE FUNCTION
# ============================================================

EARTH_RADIUS_KM = 6371.0


def haversine(lat1, lon1, lat2, lon2):

    if None in (lat1, lon1, lat2, lon2):
        return None

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    # Protect against tiny floating-point errors
    a = min(1.0, max(0.0, a))

    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# ============================================================
# READ DATA
# ============================================================

print("Reading trajectory data...")

df = pl.read_parquet(INPUT_FILE)

print("Input records:", df.height)


# ============================================================
# SORT + ROW ID
# ============================================================

df = (
    df
    .sort(["mmsi", "base_date_time"])
    .with_row_index("row_id")
)


# ============================================================
# FIND DUPLICATE TIMESTAMPS
# ============================================================

duplicate_groups = (
    df
    .group_by(["mmsi", "base_date_time"])
    .len()
    .filter(pl.col("len") > 1)
)

print(
    "Duplicate timestamp groups:",
    duplicate_groups.height
)


# ============================================================
# RESOLVE DUPLICATES
# ============================================================

rows_to_remove = set()

audit_records = []

# Work vessel by vessel.
for mmsi, vessel_df in df.group_by("mmsi", maintain_order=True):

    # group_by returns tuple for the key
    if isinstance(mmsi, tuple):
        mmsi_value = mmsi[0]
    else:
        mmsi_value = mmsi

    vessel_rows = vessel_df.to_dicts()

    i = 0

    while i < len(vessel_rows):

        current_time = vessel_rows[i]["base_date_time"]

        # Find all records having this exact timestamp
        j = i

        while (
            j < len(vessel_rows)
            and vessel_rows[j]["base_date_time"] == current_time
        ):
            j += 1

        group = vessel_rows[i:j]

        # Only process actual duplicates
        if len(group) > 1:

            # Previous observation
            previous = vessel_rows[i - 1] if i > 0 else None

            # Next observation
            next_row = vessel_rows[j] if j < len(vessel_rows) else None

            candidate_scores = []

            for candidate in group:

                score = 0.0
                valid_comparisons = 0

                # --------------------------------------------
                # Distance from previous observation
                # --------------------------------------------

                if previous is not None:

                    d_prev = haversine(
                        previous["latitude"],
                        previous["longitude"],
                        candidate["latitude"],
                        candidate["longitude"]
                    )

                    if d_prev is not None:
                        score += d_prev
                        valid_comparisons += 1

                # --------------------------------------------
                # Distance to next observation
                # --------------------------------------------

                if next_row is not None:

                    d_next = haversine(
                        candidate["latitude"],
                        candidate["longitude"],
                        next_row["latitude"],
                        next_row["longitude"]
                    )

                    if d_next is not None:
                        score += d_next
                        valid_comparisons += 1

                if valid_comparisons > 0:

                    candidate_scores.append({
                        "row_id": candidate["row_id"],
                        "score": score
                    })

            # ------------------------------------------------
            # Choose candidate with smallest trajectory score
            # ------------------------------------------------

            if candidate_scores:

                candidate_scores.sort(
                    key=lambda x: x["score"]
                )

                best = candidate_scores[0]

                # Second best candidate
                second_best = (
                    candidate_scores[1]
                    if len(candidate_scores) > 1
                    else None
                )

                # ------------------------------------------------
                # Determine confidence
                # ------------------------------------------------

                if second_best is not None:

                    best_score = best["score"]
                    second_score = second_best["score"]

                    if second_score > 0:

                        improvement = (
                            second_score - best_score
                        ) / second_score

                    else:
                        improvement = 0.0

                else:

                    best_score = best["score"]
                    second_score = None
                    improvement = 1.0

                # ------------------------------------------------
                # Keep best candidate
                # ------------------------------------------------

                for candidate in group:

                    if candidate["row_id"] != best["row_id"]:

                        rows_to_remove.add(candidate["row_id"])

                audit_records.append({
                    "mmsi": mmsi_value,
                    "base_date_time": current_time,

                    "kept_row_id": best["row_id"],

                    "candidate_1_score_km":
                        best_score,

                    "candidate_2_score_km":
                        second_score,

                    "relative_improvement":
                        improvement,

                    "candidate_count":
                        len(group)
                })

        i = j


# ============================================================
# CREATE AUDIT DATAFRAME
# ============================================================

audit_df = pl.DataFrame(audit_records)


# ============================================================
# REMOVE LOSING DUPLICATE RECORDS
# ============================================================

df_final = (
    df
    .filter(
        ~pl.col("row_id").is_in(list(rows_to_remove))
    )
    .drop("row_id")
)


# ============================================================
# CHECK RESULTS
# ============================================================

remaining_duplicates = (
    df_final
    .group_by(["mmsi", "base_date_time"])
    .len()
    .filter(pl.col("len") > 1)
)

zero_time = df_final.filter(
    pl.col("delta_seconds") <= 0
)

print("\n========== DUPLICATE RESOLUTION ==========")

print(
    "Original records:",
    df.height
)

print(
    "Records removed:",
    len(rows_to_remove)
)

print(
    "Final records:",
    df_final.height
)

print(
    "Duplicate groups remaining:",
    remaining_duplicates.height
)

print(
    "Rows with delta_seconds <= 0:",
    zero_time.height
)


# ============================================================
# SAVE
# ============================================================

df_final.write_parquet(OUTPUT_FILE)

audit_df.write_parquet(AUDIT_FILE)

print("\n========== FILES SAVED ==========")

print("Final trajectory:")
print(OUTPUT_FILE)

print("\nDuplicate resolution audit:")
print(AUDIT_FILE)