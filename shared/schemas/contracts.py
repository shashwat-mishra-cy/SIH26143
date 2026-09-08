from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    speed: float | None = Field(
        default=None,
        ge=0,
    )

    heading: float | None = Field(
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

class DriftParticleTrajectory(BaseModel):
    particle_id: str | int

    trajectory: list[TrajectoryPoint]


class DriftResult(BaseModel):
    spill_id: str

    source_origin: Coordinate

    source_region: dict[str, Any]

    estimated_origin_timestamp: datetime

    estimated_source_time_start: datetime | None = None

    estimated_source_time_end: datetime | None = None

    confidence: float = Field(
        ge=0,
        le=1,
    )

    oil_trajectory: list[TrajectoryPoint]

    particle_trajectories: list[
        DriftParticleTrajectory
    ] = []


# ============================================================
# PERSON 3 — AIS VESSEL ASSOCIATION
# ============================================================

class VesselScores(BaseModel):
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


class VesselEvidence(BaseModel):
    distance_to_source_km: float | None = Field(
        default=None,
        ge=0,
    )

    time_difference_minutes: float | None = None

    reasons: list[str] = []


class VesselCandidate(BaseModel):
    rank: int = Field(
        ge=1,
    )

    mmsi: str

    vessel_name: str | None = None

    association_score: float = Field(
        ge=0,
        le=1,
    )

    scores: VesselScores = Field(
        default_factory=VesselScores,
    )

    evidence: VesselEvidence = Field(
        default_factory=VesselEvidence,
    )

    trajectory: list[
        VesselTrajectoryPoint
    ]


class AISResult(BaseModel):
    spill_id: str

    vessels: list[VesselCandidate]


# ============================================================
# COMPLETE INTEGRATED ANALYSIS
# ============================================================

class SpillAnalysis(BaseModel):
    spill: SpillResult

    drift: DriftResult | None = None

    ais: AISResult | None = None
