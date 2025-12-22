# backend/routers/reports.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from ..schemas import (
    ReportCreate,
    ReportOut,
    ReportMessageCreate,
    ReportMessageOut,
    ReportWithMessages,
)
from ..database import get_connection
from ..deps import require_role
from .websockets import manager   # your ConnectionManager instance

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------- NOTIFICATION HELPERS (WEBSOCKETS) ----------

async def _notify_admins(payload: dict):
    """
    Send a WS message to all users with role admin/operations.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role IN ('admin', 'operations');")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        await manager.send_personal_message(payload, r["id"])


async def _notify_instructor(instructor_id: int, payload: dict):
    """
    Send a WS message to the user account linked to this instructor.
    (users.instructor_id = instructors.id)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM users WHERE instructor_id = %s;",
        (instructor_id,),
    )
    user_row = cur.fetchone()
    cur.close()
    conn.close()

    if user_row:
        await manager.send_personal_message(payload, user_row["id"])


# ---------- ROUTES ----------

@router.post("/", response_model=ReportOut)
async def create_report(
    report: ReportCreate,
    current_user = Depends(require_role("instructor")),
):
    """
    Instructor creates a new report (with a title + first message).
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 1) Insert report
        cur.execute(
            """
            INSERT INTO reports (instructorid, title, status, cubesat_id, image_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, instructorid, title, status, cubesat_id, image_url, created_at, updated_at;
            """,
            (
                current_user["instructor_id"],
                report.title,
                "open",
                report.cubesat_id,
                report.image_url,
            ),
        )
        r = cur.fetchone()

        # 2) Insert first message
        cur.execute(
            """
            INSERT INTO report_messages (report_id, sender_role, sender_user_id, message)
            VALUES (%s, %s, %s, %s)
            RETURNING id, report_id, sender_role, sender_user_id, message, created_at;
            """,
            (r["id"], "instructor", current_user["id"], report.message),
        )
        m = cur.fetchone()

        conn.commit()
    finally:
        cur.close()
        conn.close()

    # Build WS payload
    payload = {
        "type": "report_created",
        "report": {
            "id": r["id"],
            "instructor_id": r["instructorid"],
            "title": r["title"],
            "status": r["status"],
            "cubesat_id": r.get("cubesat_id"),
            "image_url": r.get("image_url"),
            "created_at": r["created_at"].isoformat(),
            "updated_at": r["updated_at"].isoformat(),
        },
        "message": {
            "id": m["id"],
            "report_id": m["report_id"],
            "sender_role": m["sender_role"],
            "sender_user_id": m["sender_user_id"],
            "message": m["message"],
            "created_at": m["created_at"].isoformat(),
        },
    }
    await _notify_admins(payload)

    return ReportOut(
        id=r["id"],
        instructor_id=r["instructorid"],
        instructor_name=current_user.get("full_name"),
        title=r["title"],
        status=r["status"],
        cubesat_id=r.get("cubesat_id"),
        image_url=r.get("image_url"), 
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


@router.get("/", response_model=List[ReportOut])
async def list_reports(
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    """
    - Instructors: see ONLY their own reports
    - Admin/operations: see ALL reports
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        if current_user["role"] == "instructor":
            cur.execute(
                """
                SELECT r.*, i.name AS instructor_name
                FROM reports r
                LEFT JOIN instructors i ON r.instructorid = i.id
                WHERE r.instructorid = %s
                ORDER BY r.status ASC, r.created_at DESC;
                """,
                (current_user["instructor_id"],),
            )
        else:
            cur.execute(
                """
                SELECT r.*, i.name AS instructor_name
                FROM reports r
                LEFT JOIN instructors i ON r.instructorid = i.id
                ORDER BY r.status ASC, r.created_at DESC;
                """
            )

        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return [
        ReportOut(
            id=r["id"],
            instructor_id=r["instructorid"],
            instructor_name=r.get("instructor_name"),
            title=r["title"],
            status=r["status"],
            cubesat_id=r.get("cubesat_id"),
            image_url=r.get("image_url"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get("/{report_id}", response_model=ReportWithMessages)
async def get_report(
    report_id: int,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    """
    Get a single report + all its messages.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT r.*, i.name AS instructor_name
            FROM reports r
            LEFT JOIN instructors i ON r.instructorid = i.id
            WHERE r.id = %s;
            """,
            (report_id,),
        )
        r = cur.fetchone()

        if not r:
            raise HTTPException(status_code=404, detail="Report not found")

        # Instructor can only see their own report
        if current_user["role"] == "instructor" and r["instructorid"] != current_user["instructor_id"]:
            raise HTTPException(status_code=403, detail="Not allowed")

        cur.execute(
            """
            SELECT *
            FROM report_messages
            WHERE report_id = %s
            ORDER BY created_at ASC;
            """,
            (report_id,),
        )
        msgs = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return ReportWithMessages(
        id=r["id"],
        instructor_id=r["instructorid"],
        instructor_name=r.get("instructor_name"),
        title=r["title"],
        status=r["status"],
        cubesat_id=r.get("cubesat_id"),
        image_url=r.get("image_url"),
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        messages=[
            ReportMessageOut(
                id=m["id"],
                report_id=m["report_id"],
                sender_role=m["sender_role"],
                sender_user_id=m["sender_user_id"],
                message=m["message"],
                created_at=m["created_at"],
            )
            for m in msgs
        ],
    )


@router.post("/{report_id}/messages", response_model=ReportMessageOut)
async def add_message(
    report_id: int,
    body: ReportMessageCreate,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    """
    Add a message to an existing report.
    - Instructor: can only reply to their own reports
    - Admin/operations: can reply to any report
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Get report
        cur.execute("SELECT * FROM reports WHERE id = %s;", (report_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Report not found")

        # Instructor can only reply to own report
        if current_user["role"] == "instructor" and r["instructorid"] != current_user["instructor_id"]:
            raise HTTPException(status_code=403, detail="Not allowed")

        sender_role = "admin" if current_user["role"] in ("admin", "operations") else "instructor"

        # Insert message
        cur.execute(
            """
            INSERT INTO report_messages (report_id, sender_role, sender_user_id, message)
            VALUES (%s, %s, %s, %s)
            RETURNING id, report_id, sender_role, sender_user_id, message, created_at;
            """,
            (report_id, sender_role, current_user["id"], body.message),
        )
        m = cur.fetchone()

        # Update status + updated_at
        if sender_role == "admin" and r["status"] == "open":
            new_status = "in_progress"
        else:
            new_status = r["status"]

        cur.execute(
            """
            UPDATE reports
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s;
            """,
            (new_status, report_id),
        )

        conn.commit()
    finally:
        cur.close()
        conn.close()

    message_out = ReportMessageOut(
        id=m["id"],
        report_id=m["report_id"],
        sender_role=m["sender_role"],
        sender_user_id=m["sender_user_id"],
        message=m["message"],
        created_at=m["created_at"],
    )

    # Build WS payload
    payload = {
        "type": "report_message",
        "report_id": report_id,
        "status": new_status,
        "message": {
            "id": message_out.id,
            "sender_role": message_out.sender_role,
            "sender_user_id": message_out.sender_user_id,
            "message": message_out.message,
            "created_at": message_out.created_at.isoformat(),
        },
    }

    # Notify the other side
    if sender_role == "instructor":
        await _notify_admins(payload)
    else:
        await _notify_instructor(r["instructorid"], payload)

    return message_out


# ---------- DELETE WHOLE REPORT (THREAD) ----------

@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    """
    Delete an entire report and all its messages.

    - admin/operations: can delete ANY report
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
            if instructor_id != current_user["instructor_id"]:
                raise HTTPException(status_code=403, detail="Not allowed")
        elif role not in ("admin", "operations"):
            raise HTTPException(status_code=403, detail="Not allowed")

        # 3) Delete the report (messages removed via ON DELETE CASCADE)
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

    # 204 – No content
    return
