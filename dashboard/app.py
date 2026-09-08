from datetime import datetime, timezone, timedelta

import requests
import streamlit as st
import folium

from branca.element import Element
from streamlit_folium import st_folium


# ============================================================
# CONFIGURATION
# ============================================================

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="SIH26143 Oil Spill Attribution",
    page_icon="🌊",
    layout="wide",
)


# ============================================================
# BACKEND API
# ============================================================

def get_analysis(spill_id):
    url = f"{BACKEND_URL}/api/v1/spills/{spill_id}/analysis"

    response = requests.get(
        url,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def list_spills():
    """
    Fetch the list of available spill investigations from the
    backend. Returns a list of spill JSON objects.
    """
    url = f"{BACKEND_URL}/api/v1/spills"

    response = requests.get(
        url,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# USER TIMESTAMP
# ============================================================

def parse_user_timestamp(value):
    """
    Parse a user-supplied ISO-8601 UTC timestamp.

    Returns a timezone-aware UTC datetime, or None when the
    value is empty or invalid. No timestamp is ever generated.
    """
    value = value.strip()

    if not value:
        return None

    try:

        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except ValueError:

        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def put_spill_timestamp(spill_id, timestamp_iso):
    """
    Store a user-supplied observation timestamp in the backend.
    The backend persists it with provenance 'user'.
    """
    url = (
        f"{BACKEND_URL}/api/v1/spills/"
        f"{spill_id}/timestamp"
    )

    response = requests.put(
        url,
        json={"detection_timestamp": timestamp_iso},
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# TIME UTILITIES
# ============================================================

def parse_timestamp(value):
    """
    Convert an ISO-8601 timestamp into UTC datetime.
    """

    dt = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt.astimezone(timezone.utc)


def interpolate_position(
    trajectory,
    selected_time,
):
    """
    Interpolate the geographic position at selected_time.

    This is ONLY for dashboard visualization.

    Original AIS/OpenDrift observations are not modified.
    """

    if not trajectory:
        return None

    points = []

    for point in trajectory:

        points.append(
            (
                parse_timestamp(
                    point["timestamp"]
                ),
                point,
            )
        )

    points.sort(
        key=lambda item: item[0]
    )

    # Before first observation

    if selected_time <= points[0][0]:

        point = points[0][1]

        return {
            "latitude": point["latitude"],
            "longitude": point["longitude"],
        }

    # After last observation

    if selected_time >= points[-1][0]:

        point = points[-1][1]

        return {
            "latitude": point["latitude"],
            "longitude": point["longitude"],
        }

    # Between two observations

    for index in range(
        len(points) - 1
    ):

        time_a, point_a = points[index]

        time_b, point_b = points[
            index + 1
        ]

        if time_a <= selected_time <= time_b:

            total_seconds = (
                time_b - time_a
            ).total_seconds()

            if total_seconds == 0:

                fraction = 0

            else:

                fraction = (
                    selected_time - time_a
                ).total_seconds() / total_seconds


            latitude = (
                point_a["latitude"]
                + fraction
                * (
                    point_b["latitude"]
                    - point_a["latitude"]
                )
            )

            longitude = (
                point_a["longitude"]
                + fraction
                * (
                    point_b["longitude"]
                    - point_a["longitude"]
                )
            )

            return {
                "latitude": latitude,
                "longitude": longitude,
            }

    return None


def interpolate_heading(
    trajectory,
    selected_time,
):
    """
    Return the heading closest to the selected
    timeline position.

    Heading is taken from the nearest actual AIS
    observation because interpolating circular angles
    can produce incorrect results around 0/360 degrees.
    """

    if not trajectory:
        return 0

    points = []

    for point in trajectory:

        heading = point.get(
            "heading"
        )

        if heading is None:
            continue

        points.append(
            (
                parse_timestamp(
                    point["timestamp"]
                ),
                heading,
            )
        )

    if not points:
        return 0

    points.sort(
        key=lambda item: item[0]
    )

    nearest = min(
        points,
        key=lambda item: abs(
            item[0] - selected_time
        )
    )

    return nearest[1]


# ============================================================
# GEOJSON UTILITIES
# ============================================================

def polygon_points(coordinates):
    """
    Convert polygon coordinates into Folium format.

    Supports both:

    Standard GeoJSON:
    [[[lon, lat], [lon, lat], ...]]

    and the flattened dummy-data format:

    [lon, lat, lon, lat, ...]
    """

    if not coordinates:
        return []


    # Flattened format

    if isinstance(
        coordinates[0],
        (int, float),
    ):

        points = []

        for index in range(
            0,
            len(coordinates) - 1,
            2,
        ):

            longitude = coordinates[
                index
            ]

            latitude = coordinates[
                index + 1
            ]

            points.append(
                [
                    latitude,
                    longitude,
                ]
            )

        return points


    # Standard GeoJSON

    ring = coordinates[0]

    return [
        [
            latitude,
            longitude,
        ]
        for longitude, latitude in ring
    ]


# ============================================================
# TRAJECTORY VISIBILITY
# ============================================================

def visible_trajectory(
    trajectory,
    selected_time,
):
    """
    Return the trajectory visible up to selected_time.

    Crucially, if selected_time falls between two actual
    observations, the interpolated position is appended.

    Therefore the line ends exactly at the moving marker.
    """

    if not trajectory:
        return []


    if selected_time is None:
        return trajectory


    sorted_points = sorted(
        trajectory,
        key=lambda point: parse_timestamp(
            point["timestamp"]
        )
    )


    visible = [
        point
        for point in sorted_points
        if parse_timestamp(
            point["timestamp"]
        ) <= selected_time
    ]


    interpolated = interpolate_position(
        sorted_points,
        selected_time,
    )


    if interpolated is None:
        return visible


    # Determine whether selected time already
    # corresponds to an actual observation.

    actual_match = any(
        parse_timestamp(
            point["timestamp"]
        ) == selected_time
        for point in sorted_points
    )


    if actual_match:
        return visible


    # Add interpolated point so trail reaches
    # exactly to the moving marker.

    visible = list(visible)

    visible.append(
        {
            "timestamp": selected_time.isoformat(),
            "latitude": interpolated[
                "latitude"
            ],
            "longitude": interpolated[
                "longitude"
            ],
        }
    )

    return visible


# ============================================================
# SHIP MARKER
# ============================================================

def add_ship_marker(
    map_object,
    latitude,
    longitude,
    heading,
    color,
    vessel_name,
    rank,
    mmsi,
    association_score,
):
    """
    Add a colored, heading-aware ship marker.

    The ship is an inline SVG so its color can match
    the vessel trajectory.
    """

    popup_html = (
        f"<b>{vessel_name}</b><br>"
        f"Rank: {rank}<br>"
        f"MMSI: {mmsi}<br>"
        f"Association: "
        f"{association_score * 100:.1f}%<br>"
        f"Heading: {heading:.1f}°"
    )


    ship_html = f"""
    <div style="
        transform: rotate({heading}deg);
        transform-origin: center center;
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
    ">
        <svg
            width="32"
            height="32"
            viewBox="0 0 100 100"
            xmlns="http://www.w3.org/2000/svg"
        >
            <path
                d="
                    M50 5
                    L70 35
                    L68 68
                    L88 78
                    L76 91
                    L24 91
                    L12 78
                    L32 68
                    L30 35
                    Z
                "
                fill="{color}"
                stroke="white"
                stroke-width="5"
            />

            <rect
                x="38"
                y="28"
                width="24"
                height="30"
                rx="4"
                fill="white"
            />

            <rect
                x="43"
                y="33"
                width="14"
                height="10"
                fill="{color}"
            />
        </svg>
    </div>
    """


    icon = folium.DivIcon(
        html=ship_html,
        icon_size=(34, 34),
        icon_anchor=(17, 17),
    )


    folium.Marker(
        location=[
            latitude,
            longitude,
        ],
        icon=icon,
        tooltip=(
            f"Rank {rank} — "
            f"{vessel_name}"
        ),
        popup=folium.Popup(
            popup_html,
            max_width=300,
        ),
    ).add_to(
        map_object
    )


# ============================================================
# HEADER
# ============================================================

st.title(
    "🌊 SIH26143 — Oil Spill Attribution Dashboard"
)

st.caption(
    "Satellite detection → Ocean drift reconstruction → "
    "Historical AIS correlation"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header(
    "Analysis"
)

# Load the list of available spill investigations from the
# backend. The dashboard must not depend on any hardcoded spill id.
try:

    spills_list = list_spills()

except requests.exceptions.RequestException as error:

    st.error(
        "Unable to connect to the FastAPI backend."
    )

    st.code(
        str(error)
    )

    st.stop()

spill_ids = [
    item["spill_id"]
    for item in spills_list
]

if not spill_ids:

    st.warning(
        "No spill investigations are available yet."
    )

    # Nothing to investigate yet: do not call the analysis endpoint.
    st.stop()


spill_id = st.sidebar.selectbox(
    "Spill ID",
    options=spill_ids,
    key="selected_spill_id",
)

st.sidebar.divider()

st.sidebar.subheader(
    "Satellite Observation Timestamp"
)

user_timestamp_input = st.sidebar.text_input(
    "Observation / Acquisition Time (UTC)",
    value="",
    placeholder="e.g. 2025-01-01T10:30:00Z",
    help=(
        "Optional. When supplied and valid, this value is "
        "stored as the spill detection timestamp with "
        "provenance 'user'. The system never invents a "
        "timestamp."
    ),
)

if st.sidebar.button(
    "Save Observation Timestamp"
):
    parsed_timestamp = parse_user_timestamp(
        user_timestamp_input
    )

    if parsed_timestamp is None:

        if not user_timestamp_input.strip():

            st.sidebar.info(
                "No timestamp supplied — nothing was saved."
            )

        else:

            st.sidebar.error(
                "Invalid timestamp. "
                "Expected ISO 8601 UTC, "
                "e.g. 2025-01-01T10:30:00Z"
            )

    else:

        try:

            put_spill_timestamp(
                spill_id,
                parsed_timestamp.isoformat(),
            )

        except requests.exceptions.RequestException as error:

            st.sidebar.error(
                f"Unable to save timestamp: {error}"
            )

        else:

            # Force a fresh timeline range with the new anchor.
            st.session_state.pop(
                "backward_timeline",
                None,
            )

            st.rerun()


# ============================================================
# LOAD ANALYSIS
# ============================================================

try:

    analysis = get_analysis(
        spill_id
    )

except requests.exceptions.RequestException as error:

    st.error(
        "Unable to connect to the FastAPI backend."
    )

    st.code(
        str(error)
    )

    st.stop()


spill = analysis[
    "spill"
]

drift = analysis.get(
    "drift"
)

ais = analysis.get(
    "ais"
)


# ============================================================
# SPILL DETECTION
# ============================================================

st.subheader(
    "Spill Detection"
)

confidence = spill[
    "confidence"
]


if confidence >= 0.5:

    st.success(
        "Oil spill detected"
    )

else:

    st.warning(
        "No oil spill detected"
    )


col1, col2, col3, col4 = st.columns(
    4
)


with col1:

    st.metric(
        "Confidence",
        f"{confidence * 100:.1f}%"
    )


with col2:

    st.metric(
        "Spill Area",
        f"{spill['spill_area_km2']:.2f} km²"
    )


with col3:

    st.metric(
        "Latitude",
        f"{spill['centroid']['latitude']:.4f}"
    )


with col4:

    st.metric(
        "Longitude",
        f"{spill['centroid']['longitude']:.4f}"
    )


# P1 TIMESTAMP RULE:
# detection_timestamp is optional and must never be invented.
detection_timestamp = spill.get(
    "detection_timestamp"
)

timestamp_provenance = spill.get(
    "timestamp_provenance",
    "unavailable",
)


if detection_timestamp:

    st.caption(
        f"Satellite observation timestamp: "
        f"{detection_timestamp} "
        f"(provenance: {timestamp_provenance})"
    )

else:

    st.warning(
        "Satellite observation timestamp unavailable — "
        "time-synchronized drift reconstruction and "
        "AIS temporal correlation cannot be performed."
    )


# ============================================================
# PREPARE TIMELINE DATA
# ============================================================

# P1 TIMESTAMP RULE:
# detection_timestamp is optional and must never be invented.
# The synchronized calendar timeline is ONLY built when a valid
# detection timestamp anchors it. Without it, no timeline is
# fabricated from system time, file time, or fixed steps.
detection_time = None

if detection_timestamp:

    detection_time = parse_timestamp(
        detection_timestamp
    )


timeline_times = []


if detection_time is not None:

    if drift:

        for point in drift.get(
            "oil_trajectory",
            [],
        ):

            timeline_times.append(
                parse_timestamp(
                    point["timestamp"]
                )
            )

    if ais:

        for vessel in ais.get(
            "vessels",
            [],
        ):

            for point in vessel.get(
                "trajectory",
                [],
            ):

                timeline_times.append(
                    parse_timestamp(
                        point["timestamp"]
                    )
                )

    # Include satellite detection time
    timeline_times.append(
        detection_time
    )

    timeline_times = sorted(
        set(timeline_times)
    )


# Keep the timeline selection across Streamlit reruns.
# The slider is rendered below the map, but its value
# must be available before the map is constructed.

if detection_time is not None and timeline_times:
    timeline_start = timeline_times[0]
    timeline_end = timeline_times[-1]

    if "backward_timeline" not in st.session_state:
        st.session_state["backward_timeline"] = timeline_end

    selected_time = st.session_state["backward_timeline"]
else:
    selected_time = None

# ============================================================
# ============================================================
# BACKWARD VISIBLE VESSEL TRAJECTORY
# ============================================================

def backward_visible_trajectory(
    trajectory,
    selected_time,
    detection_time,
):
    """
    Show the vessel trajectory from the selected historical
    position forward to the observed detection position.
    """

    if not trajectory or selected_time is None:
        return []

    points = []

    for point in trajectory:

        timestamp = parse_timestamp(
            point["timestamp"]
        )

        if (
            timestamp >= selected_time
            and timestamp <= detection_time
        ):
            points.append(
                (
                    timestamp,
                    point,
                )
            )

    points.sort(
        key=lambda item: item[0]
    )

    interpolated = interpolate_position(
        trajectory,
        selected_time,
    )

    if interpolated:

        selected_point = {
            "timestamp": selected_time.isoformat(),
            "latitude": interpolated["latitude"],
            "longitude": interpolated["longitude"],
        }

        heading = interpolate_heading(
            trajectory,
            selected_time,
        )

        if heading is not None:
            selected_point["heading"] = heading

        points = [
            item
            for item in points
            if item[0] != selected_time
        ]

        points.insert(
            0,
            (
                selected_time,
                selected_point,
            )
        )

    return [
        point
        for _, point in points
    ]

# MAP
# ============================================================

st.subheader(
    "Evidence Map"
)


centroid = spill[
    "centroid"
]


# ------------------------------------------------------------
# Calculate initial bounds
# ------------------------------------------------------------

all_latitudes = [
    centroid["latitude"]
]

all_longitudes = [
    centroid["longitude"]
]


geometry = spill.get(
    "geometry"
)


if (
    geometry
    and geometry.get("type")
    == "Polygon"
):

    points = polygon_points(
        geometry.get(
            "coordinates",
            [],
        )
    )

    for latitude, longitude in points:

        all_latitudes.append(
            latitude
        )

        all_longitudes.append(
            longitude
        )


if drift:

    source = drift[
        "source_origin"
    ]

    all_latitudes.append(
        source["latitude"]
    )

    all_longitudes.append(
        source["longitude"]
    )


    oil_trajectory = drift.get(
        "oil_trajectory",
        []
    )

    for point in oil_trajectory:

        all_latitudes.append(
            point["latitude"]
        )

        all_longitudes.append(
            point["longitude"]
        )


if ais:

    for vessel in ais.get(
        "vessels",
        [],
    ):

        for point in vessel.get(
            "trajectory",
            [],
        ):

            all_latitudes.append(
                point["latitude"]
            )

            all_longitudes.append(
                point["longitude"]
            )


# ------------------------------------------------------------
# Preserve user's map viewport
# ------------------------------------------------------------

if "map_center" not in st.session_state:

    st.session_state.map_center = [
        centroid["latitude"],
        centroid["longitude"],
    ]


if "map_zoom" not in st.session_state:

    st.session_state.map_zoom = 10


# Create map

m = folium.Map(
    location=st.session_state.map_center,
    zoom_start=st.session_state.map_zoom,
    control_scale=True,
)


# ============================================================
# SPILL POLYGON — ALWAYS VISIBLE
# ============================================================

if (
    geometry
    and geometry.get("type")
    == "Polygon"
):

    spill_points = polygon_points(
        geometry.get(
            "coordinates",
            [],
        )
    )


    if spill_points:

        folium.Polygon(
            locations=spill_points,
            tooltip="Detected Spill Area",
            fill=True,
            fill_opacity=0.35,
        ).add_to(m)


# ============================================================
# STATIC SPILL CENTROID
# ============================================================

folium.CircleMarker(
    location=[
        centroid["latitude"],
        centroid["longitude"],
    ],
    radius=5,
    tooltip="Observed Spill Location",
    popup=(
        "<b>Observed Spill</b><br>"
        f"Detection: "
        f"{detection_timestamp or 'unavailable'}<br>"
        f"Confidence: "
        f"{confidence * 100:.1f}%"
    ),
).add_to(m)


# ============================================================
# DRIFT / OIL VISUALIZATION
# ============================================================

if drift:

    source = drift[
        "source_origin"
    ]

    oil_trajectory = drift.get(
        "oil_trajectory",
        []
    )

    origin_time = parse_timestamp(
        drift[
            "estimated_origin_timestamp"
        ]
    )

    # --------------------------------------------------------
    # Estimated source / origin marker
    # --------------------------------------------------------

    if source:

        folium.Marker(
            location=[
                source["latitude"],
                source["longitude"],
            ],
            tooltip="Estimated Source / Origin",
            popup=(
                "<b>Estimated Source / Origin</b><br>"
                f"Time: "
                f"{drift['estimated_origin_timestamp']}<br>"
                f"Confidence: "
                f"{drift['confidence'] * 100:.1f}%"
            ),
            icon=folium.Icon(
                icon="flag",
                prefix="fa",
            ),
        ).add_to(m)

    # --------------------------------------------------------
    # Source region
    # --------------------------------------------------------
    #
    # Keep the source region visible throughout the complete
    # reconstruction instead of showing it only at origin time.

    source_region = drift.get(
        "source_region"
    )

    if (
        source_region
        and source_region.get(
            "type"
        ) == "Polygon"
    ):

        source_points = polygon_points(
            source_region.get(
                "coordinates",
                [],
            )
        )

        if source_points:

            folium.Polygon(
                locations=source_points,
                tooltip="Estimated Source Region",
                fill=True,
                fill_opacity=0.15,
                weight=2,
            ).add_to(m)

    # --------------------------------------------------------
    # Progressive oil trajectory
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # Keep the existing oil trajectory timeline behavior.
    # The oil trajectory is controlled by selected_time.

    if oil_trajectory:

        if selected_time is not None:

            visible_oil = visible_trajectory(
                oil_trajectory,
                selected_time,
            )

        else:

            visible_oil = oil_trajectory

        if len(visible_oil) >= 2:

            oil_path = [
                [
                    point["latitude"],
                    point["longitude"],
                ]
                for point in visible_oil
            ]

            folium.PolyLine(
                locations=oil_path,
                color="black",
                tooltip="Reconstructed Oil Trajectory",
                weight=6,
                opacity=0.9,
            ).add_to(m)

        # ----------------------------------------------------
        # Moving oil position
        # ----------------------------------------------------

        if selected_time is not None:

            oil_position = interpolate_position(
                oil_trajectory,
                selected_time,
            )

            if oil_position:

                folium.CircleMarker(
                    location=[
                        oil_position[
                            "latitude"
                        ],
                        oil_position[
                            "longitude"
                        ],
                    ],
                    radius=8,
                    tooltip="Reconstructed Oil Position",
                    popup=(
                        "<b>Reconstructed Oil Position</b><br>"
                        f"Time: "
                        f"{selected_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    ),
                ).add_to(m)


# ============================================================
# VESSEL TRAJECTORIES
# ============================================================

if ais:

    vessels = ais.get(
        "vessels",
        []
    )

    vessel_colors = {
        1: "#ff3030",
        2: "#ffd21f",
        3: "#28c76f",
    }

    for vessel in vessels:

        trajectory = vessel.get(
            "trajectory",
            []
        )

        if not trajectory:
            continue

        rank = vessel[
            "rank"
        ]

        color = vessel_colors.get(
            rank,
            "#3388ff",
        )

        vessel_name = vessel.get(
            "vessel_name",
            "Unknown Vessel",
        )

        # ----------------------------------------------------
        # Progressive historical vessel trail
        # ----------------------------------------------------
        #
        # At detection time:
        #     only the vessel marker is shown.
        #
        # As the slider moves backward:
        #     the historical vessel trail grows.
        #
        # At origin time:
        #     the complete vessel trajectory is visible.

        if selected_time is not None:

            visible_points = backward_visible_trajectory(
                trajectory,
                selected_time,
                detection_time,
            )

        else:

            # No synchronized timeline exists:
            # show the full recorded trajectory statically.
            # Temporal correlation is NOT implied.
            visible_points = trajectory

        # ----------------------------------------------------
        # Vessel trajectory line
        # ----------------------------------------------------

        if (
            len(visible_points) >= 2
        ):

            vessel_path = [
                [
                    point["latitude"],
                    point["longitude"],
                ]
                for point in visible_points
            ]

            folium.PolyLine(
                locations=vessel_path,
                color=color,
                tooltip=(
                    f"Rank {rank} � "
                    f"{vessel_name}"
                ),
                weight=5,
                opacity=0.9,
            ).add_to(m)

        # ----------------------------------------------------
        # Current interpolated vessel position
        # ----------------------------------------------------

        if selected_time is not None:

            position = interpolate_position(
                trajectory,
                selected_time,
            )

            heading = interpolate_heading(
                trajectory,
                selected_time,
            )

        else:

            latest = trajectory[-1]

            position = {
                "latitude": latest[
                    "latitude"
                ],
                "longitude": latest[
                    "longitude"
                ],
            }

            heading = latest.get(
                "heading",
                0,
            )

        # ----------------------------------------------------
        # Ship marker
        # ----------------------------------------------------

        if position:

            add_ship_marker(
                map_object=m,
                latitude=position[
                    "latitude"
                ],
                longitude=position[
                    "longitude"
                ],
                heading=heading,
                color=color,
                vessel_name=vessel_name,
                rank=rank,
                mmsi=vessel[
                    "mmsi"
                ],
                association_score=vessel[
                    "association_score"
                ],
            )

# ============================================================
# MAP LEGEND
# ============================================================

legend_html = """
<div style="
    position: fixed;
    bottom: 30px;
    left: 30px;
    z-index: 9999;
    background-color: white;
    padding: 12px;
    border: 2px solid grey;
    border-radius: 6px;
    font-size: 13px;
">
<b>Vessel Ranking</b><br>
<span style="color:#ff3030;">■</span>
Rank 1<br>
<span style="color:#d4ad00;">■</span>
Rank 2<br>
<span style="color:#28c76f;">■</span>
Rank 3
</div>
"""

m.get_root().html.add_child(
    Element(legend_html)
)


# ============================================================
# RENDER MAP
# ============================================================

map_state = st_folium(
    m,
    width=1400,
    height=650,
    key="evidence_map",
)


# ============================================================
# SAVE MAP VIEWPORT
# ============================================================

if map_state:

    center = map_state.get(
        "center"
    )

    zoom = map_state.get(
        "zoom"
    )


    if center:

        latitude = center.get(
            "lat"
        )

        longitude = center.get(
            "lng"
        )

        if (
            latitude is not None
            and longitude is not None
        ):

            st.session_state.map_center = [
                latitude,
                longitude,
            ]


    if zoom is not None:

        st.session_state.map_zoom = zoom


# ============================================================
# BACKWARD TIMELINE
# ============================================================

st.subheader(
    "Backward Drift Reconstruction"
)


if detection_time is None:

    st.warning(
        "Satellite observation timestamp unavailable — "
        "the backward drift reconstruction cannot be "
        "synchronized to a calendar timeline. "
        "Time-dependent drift reconstruction and AIS "
        "temporal correlation are unavailable or limited; "
        "map layers are shown without time synchronization."
    )

elif timeline_times:

    timeline_start = timeline_times[0]

    timeline_end = timeline_times[-1]


    if timeline_start == timeline_end:

        selected_time = timeline_end

    else:

        # IMPORTANT:
        #
        # left  = earliest/source time
        # right = latest/spill time
        #
        # Default is RIGHT.
        #
        # Therefore dragging RIGHT → LEFT moves
        # backward through the reconstruction.

        selected_time = st.slider(
            "← Drag left to trace backward toward the estimated source",
            min_value=timeline_start,
            max_value=timeline_end,
            value=timeline_end,
            step=timedelta(
                minutes=1
            ),
            format="YYYY-MM-DD HH:mm:ss",
            key="backward_timeline",
        )


    st.info(
        "Current reconstruction time: "
        + selected_time.strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    )


    st.caption(
        "← BACKWARD HINDCAST: "
        "moving the slider from right to left traces "
        "the reconstructed event from the observed spill "
        "toward the estimated source."
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        st.metric(
            "Estimated Source Time",
            origin_time.strftime(
                "%H:%M:%S UTC"
            )
            if drift
            else "N/A",
        )


    with col2:

        st.metric(
            "Current Reconstruction Time",
            selected_time.strftime(
                "%H:%M:%S UTC"
            ),
        )


    with col3:

        st.metric(
            "Observed Spill Time",
            detection_time.strftime(
                "%H:%M:%S UTC"
            ),
        )


# ============================================================
# VESSEL RANKING
# ============================================================

st.subheader(
    "Potentially Associated Vessels"
)


if ais and ais.get(
    "vessels"
):

    for vessel in ais[
        "vessels"
    ]:

        vessel_name = (
            vessel.get(
                "vessel_name"
            )
            or "Unknown vessel"
        )


        rank = vessel[
            "rank"
        ]


        with st.expander(
            f"Rank {rank} — "
            f"{vessel_name}"
        ):

            col1, col2, col3 = st.columns(
                3
            )


            with col1:

                st.metric(
                    "Association Score",
                    f"{vessel['association_score'] * 100:.1f}%"
                )


            with col2:

                distance = vessel[
                    "evidence"
                ].get(
                    "distance_to_source_km"
                )


                if distance is not None:

                    st.metric(
                        "Distance to Source",
                        f"{distance:.1f} km"
                    )


            with col3:

                time_difference = vessel[
                    "evidence"
                ].get(
                    "time_difference_minutes"
                )


                if time_difference is not None:

                    st.metric(
                        "Time Difference",
                        f"{time_difference:.0f} min"
                    )


            scores = vessel.get(
                "scores",
                {}
            )


            st.write(
                "**Scoring Factors**"
            )


            spatial = scores.get(
                "spatial"
            )

            temporal = scores.get(
                "temporal"
            )

            trajectory_score = scores.get(
                "trajectory"
            )

            behaviour = scores.get(
                "behaviour"
            )


            st.write(
                f"Spatial: "
                f"{spatial * 100:.1f}%"
                if spatial is not None
                else "Spatial: N/A"
            )


            st.write(
                f"Temporal: "
                f"{temporal * 100:.1f}%"
                if temporal is not None
                else "Temporal: N/A"
            )


            st.write(
                f"Trajectory: "
                f"{trajectory_score * 100:.1f}%"
                if trajectory_score is not None
                else "Trajectory: N/A"
            )


            st.write(
                f"Behaviour: "
                f"{behaviour * 100:.1f}%"
                if behaviour is not None
                else "Behaviour: N/A"
            )


            reasons = vessel[
                "evidence"
            ].get(
                "reasons",
                []
            )


            if reasons:

                st.write(
                    "**Evidence**"
                )

                for reason in reasons:

                    st.write(
                        f"- {reason}"
                    )


# ============================================================
# DISCLAIMER
# ============================================================

st.divider()

st.warning(
    "Important: A vessel appearing in this ranking does not "
    "establish legal responsibility for the oil spill. Vessel "
    "association is based on spatio-temporal and trajectory "
    "correlation."
)



