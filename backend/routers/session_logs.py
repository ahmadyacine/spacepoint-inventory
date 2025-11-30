from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..schemas import SessionLogCreate, SessionLogOut, SessionLogDisplay
from ..deps import require_role
from .cubesats import REQUIRED_COUNTS

router = APIRouter(prefix="/session_logs", tags=["session_logs"])

def calculate_missing_items(log: SessionLogCreate) -> str:
    missing = []
    for field, required in REQUIRED_COUNTS.items():
        # Map schema field names to REQUIRED_COUNTS keys if they differ
        # In this case, they match exactly in the schema I defined
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
            status
        )
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
        created_at=row["created_at"]
    )


@router.get("/", response_model=List[SessionLogDisplay])
def list_session_logs(
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT l.id, l.cubesat_id, l.instructor_id, l.missing_items, l.status, l.created_at,
               c.name as cubesat_name, i.name as instructor_name
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
            instructor_name=row["instructor_name"]
        ) for row in rows
    ]
