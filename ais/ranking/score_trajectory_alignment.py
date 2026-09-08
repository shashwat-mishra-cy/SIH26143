from pathlib import Path
import math
import json
import polars as pl


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

TRAJECTORIES_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "candidate_trajectories.parquet"
)

OUTPUT_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "trajectory_alignment_scores.parquet"
)

P2_TRAJECTORY_FILE = (
    BASE_DIR
    / "output"
    / "candidates"
    / "dummy_p2_oil_trajectory.json"
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_ALIGNMENT_DISTANCE_KM = 50.0

MAX_TIME_DIFFERENCE_SECONDS = 30 * 60

# Component weights
SPATIAL_WEIGHT = 0.40
TEMPORAL_WEIGHT = 0.25
DIRECTION_WEIGHT = 0.25
COVERAGE_WEIGHT = 0.10

# Minimum number of trajectory points needed before a vessel
# receives full confidence from coverage.
FULL_COVERAGE_POINTS = 100


# ============================================================
# HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.asin(math.sqrt(a))

    return 6371.0 * c


# ============================================================
# BEARING
# ============================================================

def calculate_bearing(
    lat1,
    lon1,
    lat2,
    lon2,
):
    """
    Calculate bearing from point 1 to point 2.

    Result:
        0   = North
        90  = East
        180 = South
        270 = West
    """

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlon = math.radians(
        lon2 - lon1
    )

    x = (
        math.sin(dlon)
        * math.cos(lat2)
    )

    y = (
        math.cos(lat1)
        * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(dlon)
    )

    bearing = math.degrees(
        math.atan2(x, y)
    )

    return (
        bearing + 360
    ) % 360


# ============================================================
# ANGULAR DIFFERENCE
# ============================================================

def angular_difference(
    angle1,
    angle2,
):
    """
    Smallest absolute difference between
    two compass bearings.
    """

    difference = abs(
        angle1 - angle2
    )

    return min(
        difference,
        360 - difference,
    )


# ============================================================
# DIRECTION SCORE
# ============================================================

def direction_to_score(
    vessel_heading,
    oil_bearing,
):
    """
    Convert directional difference into
    a 0-1 compatibility score.
    """

    if (
        vessel_heading is None
        or oil_bearing is None
    ):
        return 0.5

    try:
        difference = angular_difference(
            float(vessel_heading),
            float(oil_bearing),
        )
    except (TypeError, ValueError):
        return 0.5

    # Same direction = 1
    # Opposite direction = 0
    #
    # 180 degree difference represents
    # completely opposite movement.

    score = 1.0 - (
        difference / 180.0
    )

    return max(
        0.0,
        min(1.0, score),
    )


# ============================================================
# DISTANCE SCORE
# ============================================================

def distance_to_score(
    distance_km,
):
    if distance_km is None:
        return 0.0

    if distance_km >= MAX_ALIGNMENT_DISTANCE_KM:
        return 0.0

    score = (
        1.0
        - distance_km
        / MAX_ALIGNMENT_DISTANCE_KM
    )

    return max(
        0.0,
        min(1.0, score),
    )


# ============================================================
# TIME SCORE
# ============================================================

def time_to_score(
    time_difference_seconds,
):
    if time_difference_seconds is None:
        return 0.0

    if (
        time_difference_seconds
        >= MAX_TIME_DIFFERENCE_SECONDS
    ):
        return 0.0

    score = 1.0 - (
        time_difference_seconds
        / MAX_TIME_DIFFERENCE_SECONDS
    )

    return max(
        0.0,
        min(1.0, score),
    )


# ============================================================
# COVERAGE SCORE
# ============================================================

def calculate_coverage_score(
    aligned_points,
    total_points,
):
    if total_points <= 0:
        return 0.0

    coverage = (
        aligned_points
        / total_points
    )

    # Coverage represents the proportion
    # of trajectory observations that could
    # be aligned with the oil trajectory.

    # Also account for absolute trajectory size.
    #
    # A vessel with only 3 observations should
    # not receive maximum confidence simply
    # because all 3 happened to align.

    sample_confidence = min(
        1.0,
        total_points
        / FULL_COVERAGE_POINTS,
    )

    return coverage * sample_confidence


# ============================================================
# LOAD P2 TRAJECTORY
# ============================================================

def load_p2_trajectory():

    if not P2_TRAJECTORY_FILE.exists():

        raise FileNotFoundError(
            f"P2 trajectory file not found:\n"
            f"{P2_TRAJECTORY_FILE}"
        )

    with open(
        P2_TRAJECTORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if "trajectory" not in data:

        raise ValueError(
            "P2 trajectory JSON must contain "
            "'trajectory'."
        )

    if not data["trajectory"]:

        raise ValueError(
            "P2 trajectory is empty."
        )

    return data["trajectory"]


# ============================================================
# PREPARE P2 TRAJECTORY
# ============================================================

def prepare_p2_trajectory(
    trajectory,
):

    rows = []

    for point in trajectory:

        if not all(
            key in point
            for key in [
                "timestamp",
                "latitude",
                "longitude",
            ]
        ):
            continue

        timestamp = str(
            point["timestamp"]
        )

        # P2 timestamps are UTC.
        # Remove Z internally because the
        # current AIS timestamps are timezone-naive.

        timestamp = timestamp.replace(
            "Z",
            "",
        )

        rows.append(
            {
                "oil_timestamp": timestamp,
                "oil_latitude": point[
                    "latitude"
                ],
                "oil_longitude": point[
                    "longitude"
                ],
            }
        )

    if not rows:

        raise ValueError(
            "No valid P2 trajectory points."
        )

    oil = pl.DataFrame(rows)

    oil = oil.with_columns(
        pl.col(
            "oil_timestamp"
        ).str.to_datetime(
            format="%Y-%m-%dT%H:%M:%S",
            strict=False,
        )
    )

    oil = oil.drop_nulls(
        [
            "oil_timestamp",
            "oil_latitude",
            "oil_longitude",
        ]
    )

    oil = oil.sort(
        "oil_timestamp"
    )

    return oil


# ============================================================
# ADD OIL BEARINGS
# ============================================================

def add_oil_bearings(
    oil,
):
    """
    Calculate the movement bearing between
    consecutive P2 oil trajectory points.
    """

    rows = oil.to_dicts()

    for index in range(
        len(rows)
    ):

        if index == 0:

            rows[index][
                "oil_bearing"
            ] = None

            continue

        previous = rows[
            index - 1
        ]

        current = rows[
            index
        ]

        rows[index][
            "oil_bearing"
        ] = calculate_bearing(
            previous[
                "oil_latitude"
            ],
            previous[
                "oil_longitude"
            ],
            current[
                "oil_latitude"
            ],
            current[
                "oil_longitude"
            ],
        )

    return pl.DataFrame(
        rows
    )


# ============================================================
# FIND BEST OIL MATCH
# ============================================================

def find_best_oil_match(
    vessel_lat,
    vessel_lon,
    vessel_time,
    vessel_heading,
    oil_points,
):

    best = None

    for oil_point in oil_points:

        oil_time = (
            oil_point[
                "oil_timestamp"
            ]
        )

        time_difference = abs(
            (
                vessel_time
                - oil_time
            ).total_seconds()
        )

        if (
            time_difference
            > MAX_TIME_DIFFERENCE_SECONDS
        ):
            continue

        distance = haversine_km(
            vessel_lat,
            vessel_lon,
            oil_point[
                "oil_latitude"
            ],
            oil_point[
                "oil_longitude"
            ],
        )

        spatial_score = (
            distance_to_score(
                distance
            )
        )

        temporal_score = (
            time_to_score(
                time_difference
            )
        )

        direction_score = (
            direction_to_score(
                vessel_heading,
                oil_point[
                    "oil_bearing"
                ],
            )
        )

        # Combined point-level score.
        point_score = (
            SPATIAL_WEIGHT
            * spatial_score
            +
            TEMPORAL_WEIGHT
            * temporal_score
            +
            DIRECTION_WEIGHT
            * direction_score
        )

        candidate = {
            "distance": distance,
            "time_difference": (
                time_difference
            ),
            "spatial_score": (
                spatial_score
            ),
            "temporal_score": (
                temporal_score
            ),
            "direction_score": (
                direction_score
            ),
            "point_score": point_score,
        }

        if (
            best is None
            or candidate["point_score"]
            > best["point_score"]
        ):

            best = candidate

    return best


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("IMPROVED TRAJECTORY ALIGNMENT SCORING")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Check files
    # --------------------------------------------------------

    if not TRAJECTORIES_FILE.exists():

        raise FileNotFoundError(
            f"Candidate trajectories not found:\n"
            f"{TRAJECTORIES_FILE}"
        )

    # --------------------------------------------------------
    # 2. Load P2 trajectory
    # --------------------------------------------------------

    print(
        "\nLoading P2 oil trajectory..."
    )

    p2_raw = load_p2_trajectory()

    oil = prepare_p2_trajectory(
        p2_raw
    )

    oil = add_oil_bearings(
        oil
    )

    print(
        f"P2 trajectory points: "
        f"{oil.height}"
    )

    oil_points = oil.to_dicts()

    # --------------------------------------------------------
    # 3. Load candidate trajectories
    # --------------------------------------------------------

    print(
        "\nLoading candidate vessel trajectories..."
    )

    vessels = pl.read_parquet(
        TRAJECTORIES_FILE
    )

    print(
        f"AIS trajectory records: "
        f"{vessels.height:,}"
    )

    required = [
        "mmsi",
        "timestamp",
        "latitude",
        "longitude",
    ]

    missing = [
        column
        for column in required
        if column not in vessels.columns
    ]

    if missing:

        raise ValueError(
            f"Missing columns: {missing}"
        )

    # --------------------------------------------------------
    # 4. Determine heading column
    # --------------------------------------------------------

    heading_column = None

    if "heading" in vessels.columns:
        heading_column = "heading"

    elif "cog" in vessels.columns:
        heading_column = "cog"

    # --------------------------------------------------------
    # 5. Convert AIS to records
    # --------------------------------------------------------

    selected_columns = [
        "mmsi",
        "timestamp",
        "latitude",
        "longitude",
    ]

    if heading_column:
        selected_columns.append(
            heading_column
        )

    vessel_rows = (
        vessels
        .select(selected_columns)
        .to_dicts()
    )

    # --------------------------------------------------------
    # 6. Calculate point-level alignment
    # --------------------------------------------------------

    print(
        "\nCalculating vessel ↔ oil "
        "trajectory alignment..."
    )

    alignment_rows = []

    total = len(
        vessel_rows
    )

    for index, row in enumerate(
        vessel_rows
    ):

        if index % 50000 == 0:

            print(
                f"Processed "
                f"{index:,} / "
                f"{total:,} AIS points"
            )

        heading = None

        if heading_column:

            heading = row.get(
                heading_column
            )

        match = find_best_oil_match(
            row["latitude"],
            row["longitude"],
            row["timestamp"],
            heading,
            oil_points,
        )

        if match is None:

            alignment_rows.append(
                {
                    "mmsi": row["mmsi"],
                    "timestamp": row[
                        "timestamp"
                    ],
                    "latitude": row[
                        "latitude"
                    ],
                    "longitude": row[
                        "longitude"
                    ],
                    "oil_distance_km": None,
                    "oil_time_difference_seconds": None,
                    "spatial_score": 0.0,
                    "temporal_score": 0.0,
                    "direction_score": 0.0,
                    "point_alignment_score": 0.0,
                }
            )

        else:

            alignment_rows.append(
                {
                    "mmsi": row["mmsi"],
                    "timestamp": row[
                        "timestamp"
                    ],
                    "latitude": row[
                        "latitude"
                    ],
                    "longitude": row[
                        "longitude"
                    ],
                    "oil_distance_km": match[
                        "distance"
                    ],
                    "oil_time_difference_seconds":
                        match[
                            "time_difference"
                        ],
                    "spatial_score": match[
                        "spatial_score"
                    ],
                    "temporal_score": match[
                        "temporal_score"
                    ],
                    "direction_score": match[
                        "direction_score"
                    ],
                    "point_alignment_score":
                        match[
                            "point_score"
                        ],
                }
            )

    point_scores = pl.DataFrame(
        alignment_rows
    )

    # --------------------------------------------------------
    # 7. Vessel-level aggregation
    # --------------------------------------------------------

    print(
        "\nAggregating trajectory alignment..."
    )

    vessel_scores = (
        point_scores
        .group_by("mmsi")
        .agg(
            [
                pl.col(
                    "point_alignment_score"
                )
                .mean()
                .alias(
                    "raw_trajectory_score"
                ),

                pl.col(
                    "spatial_score"
                )
                .mean()
                .alias(
                    "spatial_alignment_score"
                ),

                pl.col(
                    "temporal_score"
                )
                .mean()
                .alias(
                    "temporal_alignment_score"
                ),

                pl.col(
                    "direction_score"
                )
                .mean()
                .alias(
                    "direction_alignment_score"
                ),

                pl.col(
                    "oil_distance_km"
                )
                .filter(
                    pl.col(
                        "oil_distance_km"
                    ).is_not_null()
                )
                .min()
                .alias(
                    "minimum_oil_distance_km"
                ),

                pl.col(
                    "oil_distance_km"
                )
                .filter(
                    pl.col(
                        "oil_distance_km"
                    ).is_not_null()
                )
                .mean()
                .alias(
                    "mean_oil_distance_km"
                ),

                pl.col(
                    "oil_time_difference_seconds"
                )
                .filter(
                    pl.col(
                        "oil_time_difference_seconds"
                    ).is_not_null()
                )
                .mean()
                .alias(
                    "mean_oil_time_difference_seconds"
                ),

                pl.col(
                    "point_alignment_score"
                )
                .count()
                .alias(
                    "trajectory_points"
                ),

                pl.col(
                    "oil_distance_km"
                )
                .is_not_null()
                .cast(pl.Int64)
                .sum()
                .alias(
                    "aligned_points"
                ),
            ]
        )
    )

    # --------------------------------------------------------
    # 8. Coverage
    # --------------------------------------------------------

    vessel_scores = vessel_scores.with_columns(
        (
            pl.col("aligned_points")
            /
            pl.col("trajectory_points")
        )
        .alias(
            "alignment_coverage"
        )
    )

    # --------------------------------------------------------
# Sparse trajectory evidence
# --------------------------------------------------------
#
# A vessel with only a few AIS observations should not
# receive the same evidence strength as a vessel with
# hundreds of observations.
#
# We use a smooth sqrt-based confidence rather than a
# hard cutoff. This means sparse vessels remain eligible,
# but their trajectory evidence is weaker.
# --------------------------------------------------------

    vessel_scores = vessel_scores.with_columns(
    (
        pl.col("aligned_points").cast(pl.Float64).sqrt()
        /
        math.sqrt(FULL_COVERAGE_POINTS)
    )
    .clip(
        lower_bound=0.0,
        upper_bound=1.0,
    )
    .alias(
        "sample_confidence"
    )
    )

    # Coverage score.

    vessel_scores = vessel_scores.with_columns(
        (
            pl.col(
                "alignment_coverage"
            )
            *
            pl.col(
                "sample_confidence"
            )
        )
        .alias(
            "coverage_score"
        )
    )

    # --------------------------------------------------------
    # 9. Final trajectory score
    # --------------------------------------------------------

    vessel_scores = vessel_scores.with_columns(
        (
            pl.col(
                "spatial_alignment_score"
            )
            * SPATIAL_WEIGHT

            +

            pl.col(
                "temporal_alignment_score"
            )
            * TEMPORAL_WEIGHT

            +

            pl.col(
                "direction_alignment_score"
            )
            * DIRECTION_WEIGHT

            +

            pl.col(
                "coverage_score"
            )
            * COVERAGE_WEIGHT
        )
        .alias(
            "trajectory_score"
        )
    )

    # --------------------------------------------------------
    # 10. Add vessel metadata
    # --------------------------------------------------------

    metadata_columns = [
        "mmsi",
        "vessel_name",
        "vessel_type",
        "imo",
        "call_sign",
    ]

    available_metadata = [
        column
        for column in metadata_columns
        if column in vessels.columns
    ]

    metadata = (
        vessels
        .select(available_metadata)
        .unique(
            subset=["mmsi"],
            keep="first",
        )
    )

    vessel_scores = vessel_scores.join(
        metadata,
        on="mmsi",
        how="left",
    )

    # --------------------------------------------------------
    # 11. Sort
    # --------------------------------------------------------

    vessel_scores = vessel_scores.sort(
        [
            "trajectory_score",
            "alignment_coverage",
        ],
        descending=True,
    )

    # --------------------------------------------------------
    # 12. Save
    # --------------------------------------------------------

    vessel_scores.write_parquet(
        OUTPUT_FILE
    )

    print(
        f"\nOutput saved to:\n"
        f"{OUTPUT_FILE}"
    )

    # --------------------------------------------------------
    # 13. Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("IMPROVED TRAJECTORY ALIGNMENT SUMMARY")
    print("=" * 70)

    print(
        f"Vessels scored: "
        f"{vessel_scores.height}"
    )

    if vessel_scores.height > 0:

        print(
            "\nTrajectory score statistics:"
        )

        print(
            vessel_scores.select(
                [
                    pl.col(
                        "trajectory_score"
                    ).min().alias("min"),

                    pl.col(
                        "trajectory_score"
                    ).median().alias("median"),

                    pl.col(
                        "trajectory_score"
                    ).mean().alias("mean"),

                    pl.col(
                        "trajectory_score"
                    ).max().alias("max"),
                ]
            )
        )

        print(
            "\nTop 10 trajectory matches:"
        )

        print(
            vessel_scores.select(
                [
                    "mmsi",
                    "vessel_name",
                    "trajectory_score",
                    "spatial_alignment_score",
                    "temporal_alignment_score",
                    "direction_alignment_score",
                    "coverage_score",
                    "alignment_coverage",
                    "trajectory_points",
                    "minimum_oil_distance_km",
                    "mean_oil_distance_km",
                ]
            )
            .head(10)
        )

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()