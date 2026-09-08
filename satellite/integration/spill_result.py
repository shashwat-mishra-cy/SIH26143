from datetime import datetime, timezone
from pathlib import Path
import json

from shared.schemas.contracts import (
    Coordinate,
    SpillResult,
)


# ============================================================
# TIMESTAMP RESOLUTION
# ============================================================

def resolve_timestamp(
    metadata_timestamp: datetime | None = None,
    user_timestamp: datetime | None = None,
):
    """
    Resolve the P1 detection timestamp.

    Priority:
        1. Valid satellite metadata timestamp
        2. User-provided timestamp
        3. Unavailable

    Returns
    -------
    tuple[datetime | None, str]
        (timestamp, provenance)

    Provenance values:
        "satellite_metadata"
        "user"
        "unavailable"

    No timestamp is generated automatically.
    """

    if metadata_timestamp is not None:

        return (
            ensure_utc(metadata_timestamp),
            "satellite_metadata",
        )

    if user_timestamp is not None:

        return (
            ensure_utc(user_timestamp),
            "user",
        )

    return (
        None,
        "unavailable",
    )


# ============================================================
# UTC VALIDATION / NORMALIZATION
# ============================================================

def ensure_utc(timestamp: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware and represented in UTC.

    Naive datetimes are rejected because the shared contract
    requires timestamps to represent absolute time.
    """

    if timestamp.tzinfo is None:

        raise ValueError(
            "Timestamp must be timezone-aware and explicitly "
            "represent UTC."
        )

    return timestamp.astimezone(timezone.utc)


# ============================================================
# BUILD SPILL RESULT
# ============================================================

def build_spill_result(
    geometry_result: dict,
    spill_id: str,
    metadata_timestamp: datetime | None = None,
    user_timestamp: datetime | None = None,
) -> SpillResult:
    """
    Convert the existing P1 geographic geometry output into
    the shared SpillResult contract.

    Parameters
    ----------
    geometry_result : dict
        Output from extract_geographic_geometry().

    spill_id : str
        Unique identifier for the detected spill/scene.

    metadata_timestamp : datetime | None
        Valid satellite acquisition/observation timestamp,
        if available from real satellite metadata.

    user_timestamp : datetime | None
        Manually supplied UTC observation timestamp.

    Returns
    -------
    SpillResult
        Shared P1 -> P2 result.

    Notes
    -----
    No timestamp is generated when neither metadata nor
    user input provides one.
    """

    # --------------------------------------------------------
    # Validate detection
    # --------------------------------------------------------

    if not geometry_result.get(
        "spill_detected",
        False,
    ):

        raise ValueError(
            "Cannot build SpillResult because no spill "
            "geometry was detected."
        )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    (
        detection_timestamp,
        timestamp_provenance,
    ) = resolve_timestamp(
        metadata_timestamp=metadata_timestamp,
        user_timestamp=user_timestamp,
    )

    # --------------------------------------------------------
    # Centroid
    # --------------------------------------------------------

    centroid_data = geometry_result.get(
        "centroid"
    )

    if centroid_data is None:

        raise ValueError(
            "Spill geometry does not contain an overall centroid."
        )

    latitude = centroid_data.get(
        "lat"
    )

    longitude = centroid_data.get(
        "lon"
    )

    if latitude is None or longitude is None:

        raise ValueError(
            "Spill geometry contains an invalid centroid."
        )

    centroid = Coordinate(
        latitude=float(latitude),
        longitude=float(longitude),
    )

    # --------------------------------------------------------
    # GeoJSON geometry
    # --------------------------------------------------------

    geojson = geometry_result.get(
        "geojson"
    )

    if geojson is None:

        raise ValueError(
            "Spill geometry does not contain valid GeoJSON."
        )

    geometry = geojson.get(
        "geometry"
    )

    if geometry is None:

        raise ValueError(
            "GeoJSON result does not contain a geometry."
        )

    # --------------------------------------------------------
    # Area
    # --------------------------------------------------------

    total_area_m2 = float(
        geometry_result.get(
            "total_area_m2",
            0.0,
        )
    )

    spill_area_km2 = (
        total_area_m2 / 1_000_000.0
    )

    # --------------------------------------------------------
    # Perimeter
    # --------------------------------------------------------

    total_perimeter_m = geometry_result.get(
        "total_perimeter_m"
    )

    if total_perimeter_m is None:

        perimeter_km = None

    else:

        perimeter_km = (
            float(total_perimeter_m)
            / 1_000.0
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = float(
        geometry_result.get(
            "max_confidence",
            0.0,
        )
    )

    # --------------------------------------------------------
    # Shared result
    # --------------------------------------------------------

    return SpillResult(

        spill_id=str(
            spill_id
        ),

        detection_timestamp=(
            detection_timestamp
        ),

        timestamp_provenance=(
            timestamp_provenance
        ),

        centroid=centroid,

        geometry=geometry,

        spill_area_km2=(
            spill_area_km2
        ),

        perimeter_km=(
            perimeter_km
        ),

        confidence=confidence,
    )


# ============================================================
# LOAD GEOMETRY JSON
# ============================================================

def load_geometry_json(
    geometry_path,
):
    """
    Load an existing P1 geographic geometry JSON file.
    """

    geometry_path = Path(
        geometry_path
    )

    if not geometry_path.exists():

        raise FileNotFoundError(
            f"Geometry JSON not found:\n"
            f"{geometry_path.resolve()}"
        )

    with open(
        geometry_path,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# SAVE SPILL RESULT
# ============================================================

def save_spill_result(
    spill_result: SpillResult,
    output_path,
):
    """
    Save SpillResult as JSON.
    """

    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            spill_result.model_dump(
                mode="json"
            ),
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


# ============================================================
# DEMO
# ============================================================

def main():
    """
    Build a shared SpillResult from the current P1
    oil_00009 geometry output.

    No timestamp is supplied here because the current
    training dataset does not provide a valid acquisition
    timestamp.
    """

    geometry_path = Path(
        "spill_geometry_oil_00009.json"
    )

    output_path = Path(
        "spill_result_oil_00009.json"
    )

    geometry_result = load_geometry_json(
        geometry_path
    )

    spill_result = build_spill_result(
        geometry_result=geometry_result,
        spill_id="oil_00009",
    )

    print()
    print("=" * 70)
    print("P1 SHARED SPILL RESULT")
    print("=" * 70)

    print(
        f"Spill ID              : "
        f"{spill_result.spill_id}"
    )

    print(
        f"Detection timestamp   : "
        f"{spill_result.detection_timestamp}"
    )

    print(
        f"Timestamp provenance  : "
        f"{spill_result.timestamp_provenance}"
    )

    print(
        f"Centroid              : "
        f"{spill_result.centroid.latitude:.6f}, "
        f"{spill_result.centroid.longitude:.6f}"
    )

    print(
        f"Spill area             : "
        f"{spill_result.spill_area_km2:.6f} km²"
    )

    print(
        f"Perimeter              : "
        f"{spill_result.perimeter_km:.6f} km"
        if spill_result.perimeter_km is not None
        else "Perimeter              : None"
    )

    print(
        f"Confidence             : "
        f"{spill_result.confidence:.4f}"
    )

    print(
        f"Geometry type          : "
        f"{spill_result.geometry.get('type')}"
    )

    print("=" * 70)

    saved_path = save_spill_result(
        spill_result,
        output_path,
    )

    print(
        f"\nSaved SpillResult:"
        f"\n{saved_path.resolve()}"
    )


if __name__ == "__main__":
    main()