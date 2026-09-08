from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.schemas.contracts import (
    AISResult,
    DriftResult,
    SpillAnalysis,
    SpillResult,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "sih26143.db"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="SIH26143 Oil Spill Attribution API",
    version="0.1.0",
)


# Allow the dashboard frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class TimestampUpdate(BaseModel):
    """
    User-supplied satellite observation / acquisition timestamp.

    P1 TIMESTAMP RULE:
    This is the only supported way to attach a timestamp when
    satellite metadata provides none. The backend never invents
    a timestamp from system time, file time, or fixed steps.
    """

    detection_timestamp: datetime


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    # Person 1 satellite results
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS spills (
            spill_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        )
        """
    )

    # Person 2 drift results
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS drift_results (
            spill_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            FOREIGN KEY (spill_id) REFERENCES spills(spill_id)
        )
        """
    )

    # Person 3 AIS results
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ais_results (
            spill_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            FOREIGN KEY (spill_id) REFERENCES spills(spill_id)
        )
        """
    )

    conn.commit()
    conn.close()


init_db()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SIH26143 backend",
    }


# ============================================================
# PERSON 1 — SATELLITE
# ============================================================

@app.post("/api/v1/spills")
def create_spill(spill: SpillResult):
    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO spills (spill_id, data)
        VALUES (?, ?)
        """,
        (
            spill.spill_id,
            spill.model_dump_json(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Spill stored successfully",
        "spill_id": spill.spill_id,
    }


@app.get("/api/v1/spills")
def list_spills():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT data
        FROM spills
        ORDER BY spill_id
        """
    ).fetchall()

    conn.close()

    return [
        json.loads(row["data"])
        for row in rows
    ]


@app.get("/api/v1/spills/{spill_id}")
def get_spill(spill_id: str):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT data
        FROM spills
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Spill not found",
        )

    return json.loads(row["data"])


@app.put("/api/v1/spills/{spill_id}/timestamp")
def set_spill_timestamp(
    spill_id: str,
    update: TimestampUpdate,
):
    """
    Store a user-supplied satellite observation timestamp.

    The stored detection timestamp receives provenance "user".
    No timestamp is ever generated or invented by the system.
    """

    conn = get_connection()

    row = conn.execute(
        """
        SELECT data
        FROM spills
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    if row is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Spill not found",
        )

    data = json.loads(row["data"])

    ts = update.detection_timestamp

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)

    data["detection_timestamp"] = ts.isoformat()
    data["timestamp_provenance"] = "user"

    # Re-validate against the shared contract before persisting.
    spill = SpillResult.model_validate(data)

    conn.execute(
        """
        INSERT OR REPLACE INTO spills (spill_id, data)
        VALUES (?, ?)
        """,
        (
            spill.spill_id,
            spill.model_dump_json(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Spill timestamp stored successfully",
        "spill_id": spill_id,
        "detection_timestamp": data["detection_timestamp"],
        "timestamp_provenance": "user",
    }


# ============================================================
# PERSON 2 — DRIFT
# ============================================================

@app.put("/api/v1/spills/{spill_id}/drift")
def store_drift(
    spill_id: str,
    drift: DriftResult,
):
    # Prevent accidentally storing P2 data for another spill.
    if drift.spill_id != spill_id:
        raise HTTPException(
            status_code=400,
            detail="spill_id mismatch",
        )

    conn = get_connection()

    spill_exists = conn.execute(
        """
        SELECT 1
        FROM spills
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    if spill_exists is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Spill not found",
        )

    conn.execute(
        """
        INSERT OR REPLACE INTO drift_results
        (spill_id, data)
        VALUES (?, ?)
        """,
        (
            spill_id,
            drift.model_dump_json(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Drift result stored successfully",
        "spill_id": spill_id,
    }


@app.get("/api/v1/spills/{spill_id}/drift")
def get_drift(spill_id: str):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT data
        FROM drift_results
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Drift result not found",
        )

    return json.loads(row["data"])


# ============================================================
# PERSON 3 — AIS
# ============================================================

@app.put("/api/v1/spills/{spill_id}/ais")
def store_ais(
    spill_id: str,
    ais: AISResult,
):
    if ais.spill_id != spill_id:
        raise HTTPException(
            status_code=400,
            detail="spill_id mismatch",
        )

    conn = get_connection()

    spill_exists = conn.execute(
        """
        SELECT 1
        FROM spills
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    if spill_exists is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Spill not found",
        )

    conn.execute(
        """
        INSERT OR REPLACE INTO ais_results
        (spill_id, data)
        VALUES (?, ?)
        """,
        (
            spill_id,
            ais.model_dump_json(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "AIS result stored successfully",
        "spill_id": spill_id,
    }


@app.get("/api/v1/spills/{spill_id}/ais")
def get_ais(spill_id: str):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT data
        FROM ais_results
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="AIS result not found",
        )

    return json.loads(row["data"])


# ============================================================
# COMPLETE ANALYSIS — DASHBOARD
# ============================================================

@app.get("/api/v1/spills/{spill_id}/analysis")
def get_analysis(spill_id: str):
    conn = get_connection()

    spill_row = conn.execute(
        """
        SELECT data
        FROM spills
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    if spill_row is None:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Spill not found",
        )

    drift_row = conn.execute(
        """
        SELECT data
        FROM drift_results
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    ais_row = conn.execute(
        """
        SELECT data
        FROM ais_results
        WHERE spill_id = ?
        """,
        (spill_id,),
    ).fetchone()

    conn.close()

    # Validate everything again using our shared schemas.
    spill = SpillResult.model_validate(
        json.loads(spill_row["data"])
    )

    drift = None

    if drift_row:
        drift = DriftResult.model_validate(
            json.loads(drift_row["data"])
        )

    ais = None

    if ais_row:
        ais = AISResult.model_validate(
            json.loads(ais_row["data"])
        )

    analysis = SpillAnalysis(
        spill=spill,
        drift=drift,
        ais=ais,
    )

    return analysis.model_dump(mode="json")