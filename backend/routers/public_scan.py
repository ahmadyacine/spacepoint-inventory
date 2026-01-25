from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from ..database import get_connection
from .cubesats import REQUIRED_COUNTS


router = APIRouter(prefix="/public", tags=["public"])

class SessionLogIn(BaseModel):
    instructor_name: Optional[str] = None
    missing_items: str  # keep as TEXT for now (same as your table)
    status: Optional[str] = "pending_refill"



DB_TO_API = {
    "structures": "structures",
    "currentsensors": "current_sensors",
    "tempsensors": "temp_sensors",
    "fram": "fram",
    "sdcard": "sd_card",
    "reactionwheel": "reaction_wheel",
    "mpu": "mpu",
    "gps": "gps",
    "motordriver": "motor_driver",
    "phillipsscrewdriver": "phillips_screwdriver",
    "screwgauge3d": "screw_gauge_3d",
    "standofftool3d": "standoff_tool_3d",

    # these are already snake_case in DB
    "cdhs_board": "cdhs_board",
    "eps_board": "eps_board",
    "adcs_board": "adcs_board",
    "esp32_cam": "esp32_cam",
    "esp32": "esp32",
    "magnetorquer": "magnetorquer",
    "buck_converter_module": "buck_converter_module",
    "li_ion_battery": "li_ion_battery",
    "pin_socket": "pin_socket",
    "m3_screws": "m3_screws",
    "m3_hex_nut": "m3_hex_nut",
    "m3_9_6mm_brass_standoff": "m3_9_6mm_brass_standoff",
    "m3_10mm_brass_standoff": "m3_10mm_brass_standoff",
    "m3_10_6mm_brass_standoff": "m3_10_6mm_brass_standoff",
    "m3_20_6mm_brass_standoff": "m3_20_6mm_brass_standoff",
}




def _get_cubesat_by_token(token: str) -> Dict[str, Any]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cubesats WHERE public_token = %s;", (token,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Invalid token")
    return row


@router.get("/cubesats/{token}")
def public_cubesat_details(token: str):
    row = _get_cubesat_by_token(token)

    # 1) normalize row to snake_case keys (same as REQUIRED_COUNTS)
    c = {}
    for db_key, api_key in DB_TO_API.items():
        c[api_key] = int(row.get(db_key, 0) or 0)

    # 2) build components + missing using REQUIRED_COUNTS
    components = {}
    missing_components = {}

    for key, required in REQUIRED_COUNTS.items():
        actual = int(c.get(key, 0) or 0)
        components[key] = actual
        if actual < required:
            missing_components[key] = {
                "required": required,
                "actual": actual,
                "missing": required - actual,
            }

    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "location": row["location"],
        "delivered_date": row.get("delivereddate"),

        "components": components,
        "required_counts": REQUIRED_COUNTS,
        "missing_components": missing_components,
        "is_complete": len(missing_components) == 0,
    }



@router.get("/cubesats/{token}/qr")
def get_qr_png(token: str, type: str = "box"):
    """
    Return stored QR PNG from DB.
    type = box | check
    """
    c = _get_cubesat_by_token(token)

    if type == "box":
        png = c.get("qr_box_png")
    elif type == "check":
        png = c.get("qr_check_png")
    else:
        raise HTTPException(status_code=400, detail="type must be box or check")

    if not png:
        raise HTTPException(status_code=404, detail="QR not found")

    return Response(content=bytes(png), media_type="image/png")


@router.post("/cubesats/{token}/session-log")
def submit_session_log(token: str, payload: SessionLogIn):
    """
    Public submission endpoint (from cubesat_check.html).
    Creates a row in cubesat_session_logs.
    """
    c = _get_cubesat_by_token(token)

    conn = get_connection()
    cur = conn.cursor()

    # If you want to link to a real instructor_id, you can extend this later.
    # For now, we store instructor_name inside missing_items or create a new column.
    missing_items_text = payload.missing_items
    if payload.instructor_name:
        missing_items_text = f"Instructor: {payload.instructor_name}\n{missing_items_text}"

    cur.execute(
        """
        INSERT INTO cubesat_session_logs (cubesat_id, instructor_id, missing_items, status)
        VALUES (%s, NULL, %s, %s)
        RETURNING id;
        """,
        (c["id"], missing_items_text, payload.status or "pending_refill"),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {"ok": True, "log_id": row["id"]}
