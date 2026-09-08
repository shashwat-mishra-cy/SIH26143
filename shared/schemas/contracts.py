from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ============================================================
# COMMON GEOMETRY
# ============================================================

class Coordinate(BaseModel):
    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


class TrajectoryPoint(BaseModel):
    timestamp: datetime

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


class VesselTrajectoryPoint(TrajectoryPoint):
    """P3 AIS trajectory waypoint — actual P3 field names."""

    speed_kmh: float | None = Field(
        default=None,
        ge=0,
    )

    heading: float | None = Field(
        default=None,
        ge=0,
        le=360,
    )

    course_over_ground: float | None = Field(
        default=None,
        ge=0,
        le=360,
    )


# ============================================================
# PERSON 1 — SATELLITE SPILL DETECTION
# ============================================================

class SpillResult(BaseModel):
    spill_id: str

    # Optional because P1 must never invent a timestamp.
    # None means no valid satellite/user timestamp is available.
    detection_timestamp: datetime | None = None

    # Where the timestamp came from.
    timestamp_provenance: Literal[
        "satellite_metadata",
        "user",
        "unavailable",
    ] = "unavailable"

    centroid: Coordinate

    # GeoJSON geometry / complete spill geometry.
    geometry: dict[str, Any]

    spill_area_km2: float = Field(
        ge=0,
    )

    perimeter_km: float | None = Field(
        default=None,
        ge=0,
    )

    confidence: float = Field(
        ge=0,
        le=1,
    )


# ============================================================
# PERSON 2 — DRIFT / SOURCE RECONSTRUCTION
# ============================================================
#
# Actual P2 output contract (schema_version 1.0). The real P2
# payload supplies detection / source_time / source_support / model /
# status — NOT the legacy draft fields below (source_origin, etc.).
# Those legacy fields stay optional for backward compatibility only; a
# real P2 payload must never be required to invent them.

class DriftParticleTrajectory(BaseModel):
    """Legacy optional — kept for pre-1.0 P2 payloads."""

    particle_id: str | int

    trajectory: list[TrajectoryPoint]


class P2Detection(BaseModel):
    """Detection anchor echoed by P2 (spill observation time/position)."""

    timestamp: datetime | None = None

    latitude: float = Field(
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ge=-180,
        le=180,
    )


class P2SourceTime(BaseModel):
    """Estimated source / release time result."""

    # P2 rule: candidate MUST be nullable — P2 may report an
    # indeterminate source origin and must not be forced to invent one.

    candidate: datetime | None = None

    # Actual P2 status value (open set:「estimated」,
    #「indeterminate_conflicting_minima」,…).

    status: str


class P2SourceSupportRegion(BaseModel):
    """One HDR source-support region 及 its area."""

    geometry: dict[str, Any]

    area_km2: float = Field(
        ge=0,
    )


class P2SourceSupport(BaseModel):
    """HDR 50 / HDR 90 source-support regions."""

    hdr_50: P2SourceSupportRegion

    hdr_90: P2SourceSupportRegion





class P2ModelMetadata(BaseModel):
    """P2 hindcast model configuration."""

    particle_count: int = Field(
        ge=0,
    )

    backward_duration_hours: float = Field(
        ge=0,
    )

    time_step_minutes: float = Field(
        ge=0,
    )

    horizontal_diffusivity_m2_s: float = Field(
        ge=0,
    )


class DriftResult(BaseModel):
    """Final P2 — drift / source reconstruction output contract."""

    schema_version: str = "1.0"

    spill_id: str

    detection: P2Detection

    source_time: P2SourceTime

    source_support: P2SourceSupport | None = None

    model: P2ModelMetadata

    status: str

    # ---- Legacy pre-1.0 draft fields — optional backward compat----
    # The real P2 output does NOT supply these; none of them are
    # required. None / [] means「not provided」— never fabricated.

    source_origin: Coordinate | None = None

    source_region: dict[str, Any] | None = None

    estimated_origin_timestamp: datetime | None = None

    estimated_source_time_start: datetime | None = None

    estimated_source_time_end: datetime | None = None

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    oil_trajectory: list[TrajectoryPoint] = []

    particle_trajectories: list[
        DriftParticleTrajectory
    ] = []


# ============================================================
# PERSON 3 — AIS VESSEL ASSOCIATION
# ============================================================
#
# Actual P3 output contract (module / version / status / description /
# attribution_note / top_vessels). The legacy "vessels" list is kept
# for backward compatibility and auto-synced from top_vessels.

class P3Scores(BaseModel):
    """Vessel correlation sub-scores — all 0–1, nullable."""

    spatial: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    temporal: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    trajectory: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    behaviour: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    data_quality: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class P3Evidence(BaseModel):
    """Spatio-temporal evidence attached to a candidate vessel."""

    distance_to_source_km: float | None = Field(
        default=None,
        ge=0,
    )

    closest_observation_time: datetime | None = None

    closest_latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    closest_longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    closest_speed_kmh: float | None = Field(
        default=None,
        ge=0,
    )

    closest_heading: float | None = Field(
        default=None,
        ge=0,
        le=360,
    )

    behaviour_anomaly_records: list[Any] = []

    data_quality_anomaly_records: list[Any] = []

    trajectory_points: int | None = Field(
        default=None,
        ge=0,
    )

    aligned_points: int | None = Field(
        default=None,
        ge=0,
    )

    alignment_coverage: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    mean_oil_distance_km: float | None = Field(
        default=None,
        ge=0,
    )

    mean_oil_time_difference_seconds: float | None = None


class VesselCandidate(BaseModel):
    """Ranked candidate vessel — actual P3 vessel fields."""

    rank: int = Field(
        ge=1,
    )

    mmsi: str

    vessel_name: str | None = None

    vessel_type: str | int | None = None

    imo: str | int | None = None

    call_sign: str | None = None

    association_score: float = Field(
        ge=0,
        le=1,
    )

    scores: P3Scores = Field(
        default_factory=P3Scores,
    )

    evidence: P3Evidence = Field(
        default_factory=P3Evidence,
    )

    trajectory: list[
        VesselTrajectoryPoint
    ] = []


class AISResult(BaseModel):
    """Final P3 — AIS vessel correlation output contract."""

    module: str = "P3_AIS_VESSEL_CORRELATION"

    version: str = "1.0"

    status: Literal[
        "prototype",
        "no_candidates",
    ] = "prototype"

    description: str | None = None

    attribution_note: str | None = None

    # Legacy / P4 routing key — the upstream P3 payload may omit
    # it; P4 supplies the spill correlation key when storing results..

    spill_id: str | None = None

    top_vessels: list[VesselCandidate] = []

    # Legacy pre-1.0 alias — auto-synced from/top_vessels so older
    # consumers reading "vessels" keep working with real P3 payloads.



    vessels: list[VesselCandidate] | None = None

    @model_validator(mode="after")
    def _sync_legacy_vessels(self):
        if not self.vessels:
            self.vessels = self.top_vessels

        if not self.top_vessels and self.vessels:
            self.top_vessels = self.vessels

        return self


# ============================================================
# COMPLETE INTEGRATED ANALYSIS
# ============================================================

class SpillAnalysis(BaseModel):
    spill: SpillResult

    drift: DriftResult | None = None

    ais: AISResult | None = None