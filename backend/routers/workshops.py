from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from ..database import get_connection
from ..schemas import WorkshopCreate, WorkshopOut
from ..deps import require_role
from .email_utils import send_workshop_email


router = APIRouter(prefix="/workshops", tags=["workshops"])


# -------------------------------------------------------
# Helper: Convert row to WorkshopOut
# -------------------------------------------------------
def row_to_workshop(row, instructor_ids: Optional[List[int]] = None) -> WorkshopOut:
    """
    Convert DB row to WorkshopOut.
    Includes both legacy instructor_id and lead_instructor_id.
    """
    instructor_id_legacy = row.get("instructor_id")
    lead_instructor_id = row.get("lead_instructor_id") or instructor_id_legacy

    return WorkshopOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        workshop_type=row["workshop_type"],
        status=row["status"],
        location=row["location"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        max_participants=row["max_participants"],
        current_participants=row["current_participants"],
        requirements=row["requirements"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        lead_instructor_id=lead_instructor_id,
        instructor_id=instructor_id_legacy,
        instructors=instructor_ids or [],
        instructor_ids=instructor_ids or [],
    )


# -------------------------------------------------------
# Helper: Load workshop as dict
# -------------------------------------------------------
def get_workshop_dict(workshop_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM workshops WHERE id = %s;", (workshop_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row


# -------------------------------------------------------
# Helper: Get list of (name,email) for all instructors
# -------------------------------------------------------
def build_instructor_recipients(workshop_id: int) -> List[tuple[str, str]]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT i.name, i.email
        FROM workshop_instructors wi
        JOIN instructors i ON i.id = wi.instructor_id
        WHERE wi.workshop_id = %s;
    """, (workshop_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [(r["name"], r["email"]) for r in rows if r["email"]]


# -------------------------------------------------------
# Helper: Sync instructors for a workshop
# -------------------------------------------------------
def upsert_workshop_instructors(cursor, workshop_id: int, lead_instructor_id: Optional[int], instructor_ids: Optional[List[int]]):
    instructor_ids = instructor_ids or []
    instructor_ids = list(set(instructor_ids))

    if lead_instructor_id and lead_instructor_id not in instructor_ids:
        instructor_ids.append(lead_instructor_id)

    cursor.execute("DELETE FROM workshop_instructors WHERE workshop_id = %s;", (workshop_id,))

    for iid in instructor_ids:
        cursor.execute(
            """
            INSERT INTO workshop_instructors (workshop_id, instructor_id, is_lead)
            VALUES (%s, %s, %s)
            ON CONFLICT (workshop_id, instructor_id)
            DO UPDATE SET is_lead = EXCLUDED.is_lead;
            """,
            (workshop_id, iid, iid == lead_instructor_id),
        )


# -------------------------------------------------------
# Create Workshop
# -------------------------------------------------------
@router.post("/", response_model=WorkshopOut)
def create_workshop(workshop: WorkshopCreate, current_user=Depends(require_role("admin", "operations"))):
    conn = get_connection()
    cur = conn.cursor()

    lead_id = workshop.lead_instructor_id
    legacy_instructor_id = lead_id

    try:
        cur.execute(
            """
            INSERT INTO workshops (
                title, description, workshop_type, status, location,
                instructor_id, lead_instructor_id,
                start_date, end_date,
                max_participants, current_participants,
                requirements, notes
            )
            VALUES (%s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s)
            RETURNING *
            """,
            (
                workshop.title,
                workshop.description,
                workshop.workshop_type,
                workshop.status,
                workshop.location,
                legacy_instructor_id,
                lead_id,
                workshop.start_date,
                workshop.end_date,
                workshop.max_participants,
                workshop.current_participants,
                workshop.requirements,
                workshop.notes,
            ),
        )

        row = cur.fetchone()
        workshop_id = row["id"]

        upsert_workshop_instructors(cur, workshop_id, lead_id, workshop.instructor_ids)
        conn.commit()

        cur2 = conn.cursor()
        cur2.execute(
            "SELECT instructor_id FROM workshop_instructors WHERE workshop_id = %s ORDER BY instructor_id;",
            (workshop_id,)
        )
        instructor_ids = [r["instructor_id"] for r in cur2.fetchall()]
        cur2.close()

        return row_to_workshop(row, instructor_ids=instructor_ids)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------
# List Workshops
# -------------------------------------------------------
@router.get("/", response_model=List[WorkshopOut])
def list_workshops(current_user=Depends(require_role("admin", "operations", "instructor"))):
    conn = get_connection()
    cur = conn.cursor()

    try:
        if current_user["role"] == "instructor":
            cur.execute(
                """
                SELECT w.*,
                       COALESCE(json_agg(DISTINCT wi.instructor_id)
                                FILTER (WHERE wi.instructor_id IS NOT NULL), '[]') AS instructor_ids
                FROM workshops w
                LEFT JOIN workshop_instructors wi ON wi.workshop_id = w.id
                WHERE w.lead_instructor_id = %s OR wi.instructor_id = %s
                GROUP BY w.id
                ORDER BY w.start_date;
                """,
                (current_user["instructor_id"], current_user["instructor_id"])
            )
        else:
            cur.execute(
                """
                SELECT w.*,
                       COALESCE(json_agg(DISTINCT wi.instructor_id)
                                FILTER (WHERE wi.instructor_id IS NOT NULL), '[]') AS instructor_ids
                FROM workshops w
                LEFT JOIN workshop_instructors wi ON wi.workshop_id = w.id
                GROUP BY w.id
                ORDER BY w.start_date;
                """
            )

        rows = cur.fetchall()
        return [row_to_workshop(r, r.get("instructor_ids")) for r in rows]

    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------
# Get One Workshop
# -------------------------------------------------------
@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(workshop_id: int, current_user=Depends(require_role("admin", "operations", "instructor"))):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM workshops WHERE id = %s;", (workshop_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Workshop not found")

    cur.execute(
        "SELECT instructor_id FROM workshop_instructors WHERE workshop_id = %s ORDER BY instructor_id;",
        (workshop_id,)
    )
    instructor_ids = [r["instructor_id"] for r in cur.fetchall()]

    cur.close()
    conn.close()

    return row_to_workshop(row, instructor_ids=instructor_ids)


# -------------------------------------------------------
# Update Workshop
# -------------------------------------------------------
@router.put("/{workshop_id}", response_model=WorkshopOut)
def update_workshop(workshop_id: int, workshop: WorkshopCreate, current_user=Depends(require_role("admin", "operations"))):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM workshops WHERE id = %s;", (workshop_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Workshop not found")

    lead_id = workshop.lead_instructor_id

    try:
        cur.execute(
            """
            UPDATE workshops SET
                title=%s, description=%s, workshop_type=%s, status=%s, location=%s,
                instructor_id=%s, lead_instructor_id=%s,
                start_date=%s, end_date=%s,
                max_participants=%s, current_participants=%s,
                requirements=%s, notes=%s,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            RETURNING *;
            """,
            (
                workshop.title,
                workshop.description,
                workshop.workshop_type,
                workshop.status,
                workshop.location,
                lead_id,  # legacy
                lead_id,
                workshop.start_date,
                workshop.end_date,
                workshop.max_participants,
                workshop.current_participants,
                workshop.requirements,
                workshop.notes,
                workshop_id,
            ),
        )

        row = cur.fetchone()

        upsert_workshop_instructors(cur, workshop_id, lead_id, workshop.instructor_ids)
        conn.commit()

        cur2 = conn.cursor()
        cur2.execute(
            "SELECT instructor_id FROM workshop_instructors WHERE workshop_id = %s ORDER BY instructor_id;",
            (workshop_id,)
        )
        instructor_ids = [r["instructor_id"] for r in cur2.fetchall()]
        cur2.close()

        return row_to_workshop(row, instructor_ids=instructor_ids)

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()


# -------------------------------------------------------
# Delete Workshop
# -------------------------------------------------------
@router.delete("/{workshop_id}")
def delete_workshop(workshop_id: int, current_user=Depends(require_role("admin", "operations"))):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, title FROM workshops WHERE id = %s;", (workshop_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Workshop not found")

    cur.execute("DELETE FROM workshops WHERE id = %s;", (workshop_id,))
    conn.commit()

    cur.close()
    conn.close()

    return {"message": f"Workshop '{row['title']}' deleted successfully"}


# -------------------------------------------------------
# Send workshop invitations
# -------------------------------------------------------
@router.post("/{workshop_id}/send-invitations")
def send_workshop_invitations(
    workshop_id: int,
    background_tasks: BackgroundTasks,
    payload: dict | None = Body(default=None),
    current_user=Depends(require_role("admin", "operations"))
):
    workshop = get_workshop_dict(workshop_id)
    if not workshop:
        raise HTTPException(status_code=404, detail="Workshop not found")

    recipients = build_instructor_recipients(workshop_id)
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients with valid email")

    subject_override = payload.get("subject") if payload else None
    body_override = payload.get("body") if payload else None

    background_tasks.add_task(
        send_workshop_email,
        workshop,
        recipients,
        subject_override,
        body_override,
    )

    return {"message": "Workshop invitations are being sent in the background."}
