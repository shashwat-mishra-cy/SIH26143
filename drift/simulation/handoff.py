"""P2 to P3 Handoff Contract for SIH26143 Drift Module.

Provides a clean, stable structured output contract allowing downstream modules (e.g. Person 3 AIS)
to consume physical source-estimation results without knowledge of OpenDrift, KDE, HDR, ERA5, or Copernicus.
"""

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional, Union
from shapely.geometry import MultiPolygon, Polygon, mapping

SCHEMA_VERSION = "1.0"


def geometry_to_geojson(geom: Union[Polygon, MultiPolygon, Dict[str, Any]]) -> Dict[str, Any]:
    """Convert Shapely Polygon or MultiPolygon (or existing GeoJSON dict) into GeoJSON geometry dict.

    Preserves exact geometry type (Polygon vs MultiPolygon) without simplification or merging.
    """
    if isinstance(geom, dict):
        if "type" not in geom or "coordinates" not in geom:
            raise ValueError("GeoJSON dictionary must contain 'type' and 'coordinates' keys.")
        if geom["type"] not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"Geometry type must be 'Polygon' or 'MultiPolygon', got {geom.get('type')}.")
        return geom

    if isinstance(geom, (Polygon, MultiPolygon)):
        geo_dict = mapping(geom)
        # Convert tuples to lists for RFC 7946 GeoJSON compatibility
        return json.loads(json.dumps(geo_dict))

    raise TypeError(f"Geometry must be Shapely Polygon, MultiPolygon, or GeoJSON dict, got {type(geom).__name__}.")


@dataclass
class DetectionInfo:
    timestamp: str
    latitude: float
    longitude: float

    def __post_init__(self):
        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("detection.timestamp must be a non-empty string.")
        if not isinstance(self.latitude, (int, float)) or not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"detection.latitude must be float between -90 and 90, got {self.latitude}.")
        if not isinstance(self.longitude, (int, float)) or not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"detection.longitude must be float between -180 and 180, got {self.longitude}.")
        self.latitude = float(self.latitude)
        self.longitude = float(self.longitude)


@dataclass
class SourceTimeInfo:
    candidate: Optional[str]
    status: str

    def __post_init__(self):
        if self.candidate is not None:
            if not isinstance(self.candidate, str) or not self.candidate.strip():
                raise ValueError("source_time.candidate must be a non-empty string or None.")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("source_time.status must be a non-empty string.")



@dataclass
class HDRSupportInfo:
    geometry: Dict[str, Any]
    area_km2: float

    def __post_init__(self):
        if isinstance(self.geometry, (Polygon, MultiPolygon)):
            self.geometry = geometry_to_geojson(self.geometry)
        elif isinstance(self.geometry, dict):
            self.geometry = geometry_to_geojson(self.geometry)
        else:
            raise TypeError(f"HDR geometry must be Shapely Polygon/MultiPolygon or GeoJSON dict, got {type(self.geometry).__name__}.")

        if not isinstance(self.area_km2, (int, float)) or self.area_km2 < 0.0:
            raise ValueError(f"area_km2 must be a non-negative float, got {self.area_km2}.")
        self.area_km2 = float(self.area_km2)


@dataclass
class SourceSupportInfo:
    hdr_50: HDRSupportInfo
    hdr_90: HDRSupportInfo


@dataclass
class ModelMetadataInfo:
    particle_count: int
    backward_duration_hours: float
    time_step_minutes: float
    horizontal_diffusivity_m2_s: float

    def __post_init__(self):
        if not isinstance(self.particle_count, int) or self.particle_count <= 0:
            raise ValueError(f"particle_count must be a positive integer, got {self.particle_count}.")
        if not isinstance(self.backward_duration_hours, (int, float)) or self.backward_duration_hours <= 0.0:
            raise ValueError(f"backward_duration_hours must be a positive float, got {self.backward_duration_hours}.")
        if not isinstance(self.time_step_minutes, (int, float)) or self.time_step_minutes <= 0.0:
            raise ValueError(f"time_step_minutes must be a positive float, got {self.time_step_minutes}.")
        if not isinstance(self.horizontal_diffusivity_m2_s, (int, float)) or self.horizontal_diffusivity_m2_s < 0.0:
            raise ValueError(f"horizontal_diffusivity_m2_s must be a non-negative float, got {self.horizontal_diffusivity_m2_s}.")
        self.backward_duration_hours = float(self.backward_duration_hours)
        self.time_step_minutes = float(self.time_step_minutes)
        self.horizontal_diffusivity_m2_s = float(self.horizontal_diffusivity_m2_s)




@dataclass
class DriftSourceResult:
    spill_id: str
    detection: DetectionInfo
    source_time: SourceTimeInfo
    source_support: SourceSupportInfo
    model: ModelMetadataInfo
    schema_version: str = SCHEMA_VERSION
    status: str = "success"

    def __post_init__(self):
        if not isinstance(self.spill_id, str) or not self.spill_id.strip():
            raise ValueError("spill_id must be a non-empty string.")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must be a non-empty string.")

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary representation of the handoff contract."""
        return {
            "schema_version": self.schema_version,
            "spill_id": self.spill_id,
            "detection": {
                "timestamp": self.detection.timestamp,
                "latitude": self.detection.latitude,
                "longitude": self.detection.longitude,
            },
            "source_time": {
                "candidate": self.source_time.candidate,
                "status": self.source_time.status,
            },
            "source_support": {
                "hdr_50": {
                    "geometry": self.source_support.hdr_50.geometry,
                    "area_km2": self.source_support.hdr_50.area_km2,
                },
                "hdr_90": {
                    "geometry": self.source_support.hdr_90.geometry,
                    "area_km2": self.source_support.hdr_90.area_km2,
                },
            },
            "model": {
                "particle_count": self.model.particle_count,
                "backward_duration_hours": self.model.backward_duration_hours,
                "time_step_minutes": self.model.time_step_minutes,
                "horizontal_diffusivity_m2_s": self.model.horizontal_diffusivity_m2_s,
            },
            "status": self.status,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize handoff result to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriftSourceResult":
        """Reconstruct DriftSourceResult from a dictionary."""
        detection = DetectionInfo(**data["detection"])
        source_time = SourceTimeInfo(**data["source_time"])

        hdr_50 = HDRSupportInfo(**data["source_support"]["hdr_50"])
        hdr_90 = HDRSupportInfo(**data["source_support"]["hdr_90"])
        source_support = SourceSupportInfo(hdr_50=hdr_50, hdr_90=hdr_90)

        model = ModelMetadataInfo(**data["model"])

        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            spill_id=data["spill_id"],
            detection=detection,
            source_time=source_time,
            source_support=source_support,
            model=model,
            status=data.get("status", "success"),
        )


def create_drift_source_result(
    spill_id: str,
    detection_timestamp: str,
    detection_latitude: float,
    detection_longitude: float,
    source_time_status: str,
    hdr_50_geometry: Union[Polygon, MultiPolygon, Dict[str, Any]],
    hdr_50_area_km2: float,
    hdr_90_geometry: Union[Polygon, MultiPolygon, Dict[str, Any]],
    hdr_90_area_km2: float,
    particle_count: int,
    backward_duration_hours: float,
    time_step_minutes: float,
    horizontal_diffusivity_m2_s: float,
    candidate_source_time: Optional[str] = None,
    status: str = "success",
    schema_version: str = SCHEMA_VERSION,
) -> DriftSourceResult:
    """Convenience factory function to construct a DriftSourceResult handoff object."""
    detection = DetectionInfo(
        timestamp=detection_timestamp,
        latitude=detection_latitude,
        longitude=detection_longitude,
    )
    source_time = SourceTimeInfo(
        candidate=candidate_source_time,
        status=source_time_status,
    )
    hdr_50 = HDRSupportInfo(
        geometry=hdr_50_geometry,
        area_km2=hdr_50_area_km2,
    )
    hdr_90 = HDRSupportInfo(
        geometry=hdr_90_geometry,
        area_km2=hdr_90_area_km2,
    )
    source_support = SourceSupportInfo(
        hdr_50=hdr_50,
        hdr_90=hdr_90,
    )
    model = ModelMetadataInfo(
        particle_count=particle_count,
        backward_duration_hours=backward_duration_hours,
        time_step_minutes=time_step_minutes,
        horizontal_diffusivity_m2_s=horizontal_diffusivity_m2_s,
    )

    return DriftSourceResult(
        schema_version=schema_version,
        spill_id=spill_id,
        detection=detection,
        source_time=source_time,
        source_support=source_support,
        model=model,
        status=status,
    )
