from pathlib import Path
from datetime import datetime
import math
import polars as pl


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "output" / "anomalies" / "ais_anomalies.parquet"
OUTPUT_FILE = BASE_DIR / "output" / "candidates" / "ais_candidates.parquet"


# ---------------------------------------------------------
# DUMMY P2 INPUT
# ---------------------------------------------------------

SOURCE_LATITUDE = 40.42389
SOURCE_LONGITUDE = -73.89164

SOURCE_TIME_START = "2025-01-01T00:00:00Z"
SOURCE_TIME_END = "2025-01-01T23:59:59Z"

SEARCH_RADIUS_KM = 50.0


# ---------------------------------------------------------
# HAVERSINE DISTANCE
# ---------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_km * c


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("AIS CANDIDATE VESSEL FILTER")
    print("=" * 70)

    print("\nLoading AIS anomaly dataset...")

    df = pl.read_parquet(INPUT_FILE)

    print(f"Total AIS records: {df.height:,}")
    print(f"Unique vessels: {df['mmsi'].n_unique():,}")

    # -----------------------------------------------------
    # Parse source timestamps
    # -----------------------------------------------------

    source_start = datetime.fromisoformat(
        SOURCE_TIME_START.replace("Z", "")
    )

    source_end = datetime.fromisoformat(
        SOURCE_TIME_END.replace("Z", "")
    )

    print("\nP2 source information:")
    print(f"Source latitude : {SOURCE_LATITUDE}")
    print(f"Source longitude: {SOURCE_LONGITUDE}")
    print(f"Source time     : {SOURCE_TIME_START}")
    print(f"Source time end : {SOURCE_TIME_END}")
    print(f"Search radius   : {SEARCH_RADIUS_KM} km")

    # -----------------------------------------------------
    # TEMPORAL FILTER
    # -----------------------------------------------------

    print("\nApplying temporal filter...")

    temporal_df = df.filter(
        (pl.col("base_date_time") >= source_start)
        & (pl.col("base_date_time") <= source_end)
    )

    print(
        f"Records inside time window: "
        f"{temporal_df.height:,}"
    )

    if temporal_df.height == 0:
        print("\nNo AIS records found in the supplied time window.")
        print("Try changing the dummy P2 timestamp.")
        return

    # -----------------------------------------------------
    # CALCULATE DISTANCE
    # -----------------------------------------------------

    print("\nCalculating distance from source...")

    spatial_df = temporal_df.with_columns(
        pl.struct(["latitude", "longitude"])
        .map_elements(
            lambda row: haversine_km(
                SOURCE_LATITUDE,
                SOURCE_LONGITUDE,
                row["latitude"],
                row["longitude"],
            ),
            return_dtype=pl.Float64,
        )
        .alias("distance_to_source_km")
    )

    # -----------------------------------------------------
    # SPATIAL FILTER
    # -----------------------------------------------------

    candidates = spatial_df.filter(
        pl.col("distance_to_source_km")
        <= SEARCH_RADIUS_KM
    )

    print(
        f"Records inside {SEARCH_RADIUS_KM} km "
        f"source radius: {candidates.height:,}"
    )

    if candidates.height == 0:
        print("\nNo vessels found near the source.")
        print("Try increasing SEARCH_RADIUS_KM.")
        return

    # -----------------------------------------------------
    # FIND CLOSEST AIS POINT FOR EACH VESSEL
    # -----------------------------------------------------

    print("\nFinding closest AIS observation for each vessel...")

    closest_points = (
        candidates
        .sort(
            [
                "mmsi",
                "distance_to_source_km",
                "base_date_time",
            ]
        )
        .group_by("mmsi", maintain_order=True)
        .first()
        .select(
            [
                "mmsi",
                "base_date_time",
                "latitude",
                "longitude",
                "distance_to_source_km",
                "speed_kmh",
                "heading",
                "sog",
                "cog",
                "vessel_name",
                "vessel_type",
                "imo",
                "call_sign",
                "behaviour_anomaly_score",
                "has_behaviour_anomaly",
                "data_quality_anomaly",
            ]
        )
        .rename(
            {
                "base_date_time": "closest_observation_time",
                "latitude": "closest_latitude",
                "longitude": "closest_longitude",
                "distance_to_source_km": "minimum_distance_to_source_km",
                "speed_kmh": "closest_speed_kmh",
                "heading": "closest_heading",
                "sog": "closest_sog",
                "cog": "closest_cog",
                "behaviour_anomaly_score": "closest_behaviour_anomaly_score",
                "has_behaviour_anomaly": "closest_has_behaviour_anomaly",
                "data_quality_anomaly": "closest_data_quality_anomaly",
            }
        )
    )

    # -----------------------------------------------------
    # VESSEL-LEVEL SUMMARY
    # -----------------------------------------------------

    print("\nBuilding vessel-level candidate profiles...")

    vessel_summary = (
        candidates
        .group_by("mmsi")
        .agg(
            pl.col("vessel_name")
            .drop_nulls()
            .first()
            .alias("vessel_name"),

            pl.col("vessel_type")
            .drop_nulls()
            .first()
            .alias("vessel_type"),

            pl.col("imo")
            .drop_nulls()
            .first()
            .alias("imo"),

            pl.col("call_sign")
            .drop_nulls()
            .first()
            .alias("call_sign"),

            pl.len()
            .alias("ais_records_in_window"),

            pl.col("distance_to_source_km")
            .mean()
            .alias("mean_distance_to_source_km"),

            pl.col("base_date_time")
            .min()
            .alias("first_observation"),

            pl.col("base_date_time")
            .max()
            .alias("last_observation"),

            pl.col("speed_kmh")
            .median()
            .alias("median_speed_kmh"),

            pl.col("speed_kmh")
            .max()
            .alias("max_speed_kmh"),

            pl.col("heading")
            .median()
            .alias("median_heading"),

            (
                pl.col("has_behaviour_anomaly")
                .cast(pl.Int64)
                .sum()
            )
            .alias("behaviour_anomaly_records"),

            (
                pl.col("data_quality_anomaly")
                .cast(pl.Int64)
                .sum()
            )
            .alias("data_quality_anomaly_records"),
        )
    )

    # -----------------------------------------------------
    # JOIN CLOSEST POINT + SUMMARY
    # -----------------------------------------------------

    candidate_profiles = (
        vessel_summary
        .join(
            closest_points,
            on="mmsi",
            how="left",
        )
        .sort("minimum_distance_to_source_km")
    )

    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_profiles.write_parquet(
        OUTPUT_FILE
    )

    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    print("\n" + "=" * 70)
    print("CANDIDATE VESSELS")
    print("=" * 70)

    print(
        f"\nUnique candidate vessels: "
        f"{candidate_profiles.height:,}"
    )

    print("\nClosest vessels:")

    print(
        candidate_profiles
        .head(20)
        .select(
            [
                "mmsi",
                "vessel_name",
                "vessel_type",
                "ais_records_in_window",
                "minimum_distance_to_source_km",
                "closest_observation_time",
                "closest_latitude",
                "closest_longitude",
                "closest_speed_kmh",
                "closest_heading",
                "behaviour_anomaly_records",
                "data_quality_anomaly_records",
            ]
        )
    )

    print("\n" + "=" * 70)
    print("CANDIDATE FILTER COMPLETE")
    print("=" * 70)

    print(f"\nOutput:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()