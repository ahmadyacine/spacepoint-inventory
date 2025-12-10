# backend/routers/package_requests.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime

from ..database import get_connection
from ..deps import require_role
from ..schemas import (
    PackageRequestCreate,
    PackageRequestOut,
    PackageRequestStatusUpdate,
)
from .websockets import manager   # same as in reports

router = APIRouter(prefix="/package-requests", tags=["package_requests"])


# ---- NOTIFICATION HELPERS ----

async def _notify_coos(payload: dict):
    """
    Send a WS message to all users with role 'coo'.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE role = 'coo';")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        await manager.send_personal_message(payload, r["id"])


async def _notify_user(user_id: int, payload: dict):
    await manager.send_personal_message(payload, user_id)


# ---- ROUTES ----

@router.post("/", response_model=PackageRequestOut)
async def create_package_request(
    body: PackageRequestCreate,
    current_user = Depends(require_role("admin", "operations")),
):
    """
    Admin/operations creates a package request for COO.
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO package_requests
            (requested_by, contact_name, contact_phone, location, url_location,
             items, total_items, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id, requested_by, contact_name, contact_phone, location,
                      url_location, items, total_items, status,
                      sent_date, delivered_date, created_at, updated_at;
            """,
            (
                current_user["id"],
                body.contact_name,
                body.contact_phone,
                body.location,
                body.url_location,
                body.items,
                body.total_items,
            ),
        )
        r = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    out = PackageRequestOut(
        id=r["id"],
        requested_by=r["requested_by"],
        requested_by_name=current_user.get("full_name"),
        contact_name=r["contact_name"],
        contact_phone=r["contact_phone"],
        location=r["location"],
        url_location=r["url_location"],
        items=r["items"],
        total_items=r["total_items"],
        status=r["status"],
        sent_date=r["sent_date"],
        delivered_date=r["delivered_date"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )

    # WS payload for COO
    payload = {
        "type": "package_request_created",
        "request": {
            "id": out.id,
            "requested_by": out.requested_by,
            "requested_by_name": out.requested_by_name,
            "location": out.location,
            "items": out.items,
            "total_items": out.total_items,
            "status": out.status,
            "created_at": out.created_at.isoformat(),
        },
    }
    await _notify_coos(payload)

    return out


@router.get("/", response_model=List[PackageRequestOut])
async def list_package_requests(
    current_user = Depends(require_role("admin", "operations", "coo")),
):
    """
    - COO: see all requests
    - Admin/operations: see only their own requests
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        if current_user["role"] == "coo":
            cur.execute(
                """
                SELECT pr.*, u.full_name AS requested_by_name
                FROM package_requests pr
                LEFT JOIN users u ON pr.requested_by = u.id
                ORDER BY pr.status ASC, pr.created_at DESC;
                """
            )
        else:
            cur.execute(
                """
                SELECT pr.*, u.full_name AS requested_by_name
                FROM package_requests pr
                LEFT JOIN users u ON pr.requested_by = u.id
                WHERE pr.requested_by = %s
                ORDER BY pr.status ASC, pr.created_at DESC;
                """,
                (current_user["id"],),
            )

        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return [
        PackageRequestOut(
            id=r["id"],
            requested_by=r["requested_by"],
            requested_by_name=r.get("requested_by_name"),
            contact_name=r["contact_name"],
            contact_phone=r["contact_phone"],
            location=r["location"],
            url_location=r["url_location"],
            items=r["items"],
            total_items=r["total_items"],
            status=r["status"],
            sent_date=r["sent_date"],
            delivered_date=r["delivered_date"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]

@router.get("/my", response_model=List[PackageRequestOut])
async def list_my_requests(
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT pr.*, u.full_name AS requested_by_name
            FROM package_requests pr
            LEFT JOIN users u ON pr.requested_by = u.id
            WHERE pr.requested_by = %s
            ORDER BY pr.created_at DESC;
            """,
            (current_user["id"],),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return [
        PackageRequestOut(
            id=r["id"],
            requested_by=r["requested_by"],
            requested_by_name=r.get("requested_by_name"),
            contact_name=r["contact_name"],
            contact_phone=r["contact_phone"],
            location=r["location"],
            url_location=r["url_location"],
            items=r["items"],
            total_items=r["total_items"],
            status=r["status"],
            sent_date=r["sent_date"],
            delivered_date=r["delivered_date"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]



@router.get("/{request_id}", response_model=PackageRequestOut)
async def get_package_request(
    request_id: int,
    current_user = Depends(require_role("admin", "operations", "coo")),
):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT pr.*, u.full_name AS requested_by_name
            FROM package_requests pr
            LEFT JOIN users u ON pr.requested_by = u.id
            WHERE pr.id = %s;
            """,
            (request_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Package request not found")

        # Admin/ops can only see their own requests
        if current_user["role"] in ("admin", "operations") and r["requested_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not allowed")
    finally:
        cur.close()
        conn.close()

    return PackageRequestOut(
        id=r["id"],
        requested_by=r["requested_by"],
        requested_by_name=r.get("requested_by_name"),
        contact_name=r["contact_name"],
        contact_phone=r["contact_phone"],
        location=r["location"],
        url_location=r["url_location"],
        items=r["items"],
        total_items=r["total_items"],
        status=r["status"],
        sent_date=r["sent_date"],
        delivered_date=r["delivered_date"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


@router.patch("/{request_id}/status", response_model=PackageRequestOut)
async def update_package_request_status(
    request_id: int,
    body: PackageRequestStatusUpdate,
    current_user = Depends(require_role("admin", "operations", "coo")),
):
    """
    - COO: typically sets status to 'on_way' (with sent_date)
    - Admin/operations: confirms 'delivered' (with delivered_date)
    """
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM package_requests WHERE id = %s;", (request_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Package request not found")

        # Business rules (simple version)
        if current_user["role"] == "coo":
            # COO should not mark as delivered (up to you, you can relax this)
            if body.status == "delivered":
                raise HTTPException(status_code=403, detail="COO cannot mark as delivered")
        else:
            # admin/ops should not mark as on_way (only COO)
            if body.status == "on_way":
                raise HTTPException(status_code=403, detail="Only COO can mark as on_way")

            # admin/ops can only touch their own requests
            if r["requested_by"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not allowed")

        sent_date = body.sent_date if body.sent_date else r["sent_date"]
        delivered_date = body.delivered_date if body.delivered_date else r["delivered_date"]

        cur.execute(
            """
            UPDATE package_requests
            SET status = %s,
                sent_date = %s,
                delivered_date = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, requested_by, contact_name, contact_phone, location,
                      url_location, items, total_items, status,
                      sent_date, delivered_date, created_at, updated_at;
            """,
            (body.status, sent_date, delivered_date, request_id),
        )
        updated = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    out = PackageRequestOut(
        id=updated["id"],
        requested_by=updated["requested_by"],
        requested_by_name=None,  # will not be used here
        contact_name=updated["contact_name"],
        contact_phone=updated["contact_phone"],
        location=updated["location"],
        url_location=updated["url_location"],
        items=updated["items"],
        total_items=updated["total_items"],
        status=updated["status"],
        sent_date=updated["sent_date"],
        delivered_date=updated["delivered_date"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )

    # WS payload
    payload = {
        "type": "package_request_status",
        "request_id": out.id,
        "status": out.status,
        "sent_date": out.sent_date.isoformat() if out.sent_date else None,
        "delivered_date": out.delivered_date.isoformat() if out.delivered_date else None,
    }

    # Notify the other side
    if current_user["role"] == "coo":
        # notify requester (admin/ops) that package is on way / cancelled
        await _notify_user(out.requested_by, payload)
    else:
        # notify all COO that status changed (e.g. delivered)
        await _notify_coos(payload)

    return out





@router.post("/{request_id}/mark-received", response_model=PackageRequestOut)
async def mark_received(
    request_id: int,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT pr.*, u.full_name AS requested_by_name
            FROM package_requests pr
            LEFT JOIN users u ON pr.requested_by = u.id
            WHERE pr.id = %s;
            """,
            (request_id,),
        )
        r = cur.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Request not found")

        # فقط صاحب الطلب يقدر يعلم انه استلم
        if r["requested_by"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not allowed")

        cur.execute(
            """
            UPDATE package_requests
            SET status = 'delivered',
                delivered_date = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, requested_by, contact_name, contact_phone, location,
                      url_location, items, total_items, status,
                      sent_date, delivered_date, created_at, updated_at;
            """,
            (request_id,),
        )
        updated = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    out = PackageRequestOut(
        id=updated["id"],
        requested_by=updated["requested_by"],
        requested_by_name=r.get("requested_by_name"),
        contact_name=updated["contact_name"],
        contact_phone=updated["contact_phone"],
        location=updated["location"],
        url_location=updated["url_location"],
        items=updated["items"],
        total_items=updated["total_items"],
        status=updated["status"],
        sent_date=updated["sent_date"],
        delivered_date=updated["delivered_date"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )

    # هنا تقدر تبعت notification للـ COO لو حاب
    # await _notify_coos({...})  لو حاب تتوسع

    return out
