# backend/routers/session_logs.py

from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_connection
from ..schemas import SessionLogCreate, SessionLogOut, SessionLogDisplay
from ..deps import require_role
from .cubesats import REQUIRED_COUNTS

router = APIRouter(prefix="/session_logs", tags=["session_logs"])

# -------------------------------------------------------------------
# Mapping: field name in REQUIRED_COUNTS / missing_items
#       -> actual column name in cubesats table
# LEFT side must match REQUIRED_COUNTS keys
# RIGHT side must match your init_db() cubesats columns
# -------------------------------------------------------------------
FIELD_TO_DB_COLUMN: Dict[str, str] = {
    # Old basic kit columns
    "structures": "structures",
    "current_sensors": "currentsensors",      # logical -> DB column
    "currentsensors": "currentsensors",       # in case your REQUIRED_COUNTS already uses this
    "temp_sensors": "tempsensors",
    "tempsensors": "tempsensors",
    "fram": "fram",
    "sd_card": "sdcard",
    "sdcard": "sdcard",
    "reaction_wheel": "reactionwheel",
    "reactionwheel": "reactionwheel",
    "mpu": "mpu",
    "gps": "gps",
    "motor_driver": "motordriver",
    "motordriver": "motordriver",
    "phillips_screwdriver": "phillipsscrewdriver",
    "phillipsscrewdriver": "phillipsscrewdriver",
    "screw_gauge_3d": "screwgauge3d",
    "screwgauge3d": "screwgauge3d",
    "standoff_tool_3d": "standofftool3d",
    "standofftool3d": "standofftool3d",

    # New boards/electronics/mechanical columns you added
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


def calculate_missing_items(log: SessionLogCreate) -> str:
    """
    Build the 'missing_items' string from the counts vs REQUIRED_COUNTS.
    e.g. "fram: missing 1"
    """
    missing = []
    for field, required in REQUIRED_COUNTS.items():
        count = getattr(log, field)
        if count < required:
            missing.append(f"{field}: missing {required - count}")
    return "\n".join(missing) if missing else ""


@router.post("/", response_model=SessionLogOut)
def create_session_log(
    log: SessionLogCreate,
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    missing_str = calculate_missing_items(log)
    status = "pending_refill" if missing_str else "complete"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO cubesat_session_logs (
            cubesat_id, instructor_id, missing_items, status
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id, cubesat_id, instructor_id, missing_items, status, created_at
        """,
        (
            log.cubesat_id,
            log.instructor_id,
            missing_str if missing_str else None,
            status,
        ),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return SessionLogOut(
        id=row["id"],
        cubesat_id=row["cubesat_id"],
        instructor_id=row["instructor_id"],
        missing_items=row["missing_items"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.get("/", response_model=List[SessionLogDisplay])
def list_session_logs(
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT l.id,
               l.cubesat_id,
               l.instructor_id,
               l.missing_items,
               l.status,
               l.created_at,
               c.name AS cubesat_name,
               i.name AS instructor_name
        FROM cubesat_session_logs l
        JOIN cubesats c ON l.cubesat_id = c.id
        JOIN instructors i ON l.instructor_id = i.id
        ORDER BY l.created_at DESC;
        """
    )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        SessionLogDisplay(
            id=row["id"],
            cubesat_id=row["cubesat_id"],
            instructor_id=row["instructor_id"],
            missing_items=row["missing_items"],
            status=row["status"],
            created_at=row["created_at"],
            cubesat_name=row["cubesat_name"],
            instructor_name=row["instructor_name"],
        )
        for row in rows
    ]


# -------------------------------------------------------------------
# Approve a log = refill kit + mark log as approved
# -------------------------------------------------------------------
@router.patch("/{log_id}/approve", response_model=SessionLogDisplay)
def approve_session_log(
    log_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cur = conn.cursor()

    # 1) Load the log with cubesat + instructor info
    cur.execute(
        """
        SELECT l.id,
               l.cubesat_id,
               l.instructor_id,
               l.missing_items,
               l.status,
               l.created_at,
               c.name AS cubesat_name,
               i.name AS instructor_name
        FROM cubesat_session_logs l
        JOIN cubesats c ON l.cubesat_id = c.id
        JOIN instructors i ON l.instructor_id = i.id
        WHERE l.id = %s;
        """,
        (log_id,),
    )
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Session log not found")

    cubesat_id = row["cubesat_id"]
    missing_items = row["missing_items"] or ""

    # 2) Parse missing_items string -> { field: missing_count }
    #    Each line looks like: "fram: missing 1"
    missing_map: Dict[str, int] = {}
    for line in missing_items.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            left, right = line.split(":", 1)  # "fram", " missing 1"
            field = left.strip()
            parts = right.split()
            count = int(parts[-1])           # last token = number
            missing_map[field] = count
        except Exception:
            # ignore badly formatted lines
            continue

    # 3) Build UPDATE for cubesats – set to (required - missing)
    set_clauses = []
    values = []

    for field, missing_count in missing_map.items():
        db_column = FIELD_TO_DB_COLUMN.get(field)
        if not db_column:
            # field name not mapped to a cubesats column → skip
            continue

        required = REQUIRED_COUNTS.get(field)
        if required is None:
            # not defined in REQUIRED_COUNTS → skip
            continue

        # actual remaining in kit after this session
        new_value = max(required - missing_count, 0)

        set_clauses.append(f"{db_column} = %s")
        values.append(new_value)

    # Also handle completeness / missing summary
    if set_clauses:
        if missing_map:
            # There are missing items → kit is NOT complete
            set_clauses.append("missingitems = %s")
            values.append(missing_items)
            set_clauses.append("iscomplete = FALSE")
        else:
            # No missing items → complete kit
            set_clauses.append("missingitems = NULL")
            set_clauses.append("iscomplete = TRUE")

        update_sql = f"""
            UPDATE cubesats
            SET {", ".join(set_clauses)}
            WHERE id = %s
        """
        values.append(cubesat_id)
        cur.execute(update_sql, values)

    # 4) Mark the session log as approved
    cur.execute(
        """
        UPDATE cubesat_session_logs
        SET status = 'approved'
        WHERE id = %s
        RETURNING id, cubesat_id, instructor_id, missing_items, status, created_at;
        """,
        (log_id,),
    )
    log_row = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return SessionLogDisplay(
        id=log_row["id"],
        cubesat_id=log_row["cubesat_id"],
        instructor_id=log_row["instructor_id"],
        missing_items=log_row["missing_items"],
        status=log_row["status"],
        created_at=log_row["created_at"],
        cubesat_name=row["cubesat_name"],
        instructor_name=row["instructor_name"],
    )




# -------------------------------------------------------------------
# Delete a session log
# -------------------------------------------------------------------
@router.delete("/{log_id}", status_code=204)
def delete_session_log(
    log_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM cubesat_session_logs WHERE id = %s;", (log_id,))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Session log not found")

    conn.commit()
    cur.close()
    conn.close()
    return


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    """
    Delete an entire report (and all its messages via ON DELETE CASCADE).

    - admin/operations: can delete any report
    - instructor: can delete ONLY their own reports
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1) Find the report
        cur.execute(
            "SELECT instructorid FROM reports WHERE id = %s;",
            (report_id,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        instructor_id = row["instructorid"]

        # 2) Permission checks
        role = current_user["role"]
        if role == "instructor":
            # instructor can only delete own reports
            if instructor_id != current_user["instructor_id"]:
                raise HTTPException(status_code=403, detail="Not allowed")

        elif role not in ("admin", "operations"):
            raise HTTPException(status_code=403, detail="Not allowed")

        # 3) Delete report (messages will be removed because of ON DELETE CASCADE)
        cur.execute(
            "DELETE FROM reports WHERE id = %s;",
            (report_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Report not found")

        conn.commit()

    finally:
        cur.close()
        conn.close()

    # 204 No Content
    return