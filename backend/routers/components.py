from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..schemas import ComponentCreate, ComponentUpdate, ComponentOut, ComponentAdjust
from ..deps import require_role

router = APIRouter(prefix="/components", tags=["components"])

@router.get("/", response_model=List[ComponentOut])
def list_components(
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, category, image_url, total_quantity, created_at, updated_at
        FROM components
        ORDER BY name;
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [
        ComponentOut(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            image_url=row["image_url"],
            total_quantity=row["total_quantity"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.post("/", response_model=ComponentOut)
def create_component(
    component: ComponentCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO components (name, category, image_url, total_quantity)
        VALUES (%s, %s, %s, %s)
        RETURNING id, name, category, image_url, total_quantity, created_at, updated_at;
        """,
        (
            component.name,
            component.category,
            component.image_url,
            component.initial_quantity,
        ),
    )

    row = cursor.fetchone()
    conn.commit()

    # Optional: log initial quantity if > 0
    if component.initial_quantity > 0:
        cursor.execute(
            """
            INSERT INTO component_logs (component_id, change, reason, user_id)
            VALUES (%s, %s, %s, %s);
            """,
            (
                row["id"],
                component.initial_quantity,
                "Initial stock",
                getattr(current_user, "id", None),
            ),
        )
        conn.commit()

    cursor.close()
    conn.close()

    return ComponentOut(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        image_url=row["image_url"],
        total_quantity=row["total_quantity"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.put("/{component_id}", response_model=ComponentOut)
def update_component(
    component_id: int,
    payload: ComponentUpdate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch existing
    cursor.execute("SELECT * FROM components WHERE id = %s;", (component_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Component not found")

    new_name = payload.name or row["name"]
    new_category = payload.category or row["category"]
    new_image_url = payload.image_url if payload.image_url is not None else row["image_url"]

    cursor.execute(
        """
        UPDATE components
        SET name = %s,
            category = %s,
            image_url = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, name, category, image_url, total_quantity, created_at, updated_at;
        """,
        (new_name, new_category, new_image_url, component_id),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return ComponentOut(
        id=row["id"],
        name=row["name"],
        category=row["category"],
        image_url=row["image_url"],
        total_quantity=row["total_quantity"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/{component_id}/adjust_quantity", response_model=ComponentOut)
def adjust_quantity(
    component_id: int,
    payload: ComponentAdjust,
    current_user=Depends(require_role("admin", "operations")),
):
    if payload.delta == 0:
        raise HTTPException(status_code=400, detail="Delta must be non-zero")

    conn = get_connection()
    cursor = conn.cursor()

    # Get current quantity
    cursor.execute("SELECT total_quantity FROM components WHERE id = %s;", (component_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Component not found")

    new_qty = row["total_quantity"] + payload.delta
    if new_qty < 0:
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Quantity cannot be negative. Current: {row['total_quantity']}, delta: {payload.delta}",
        )

    # Update quantity
    cursor.execute(
        """
        UPDATE components
        SET total_quantity = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, name, category, image_url, total_quantity, created_at, updated_at;
        """,
        (new_qty, component_id),
    )
    updated = cursor.fetchone()

    # Insert log
    cursor.execute(
        """
        INSERT INTO component_logs (component_id, change, reason, user_id)
        VALUES (%s, %s, %s, %s);
        """,
        (
            component_id,
            payload.delta,
            payload.reason,
            getattr(current_user, "id", None),
        ),
    )

    conn.commit()
    cursor.close()
    conn.close()

    return ComponentOut(
        id=updated["id"],
        name=updated["name"],
        category=updated["category"],
        image_url=updated["image_url"],
        total_quantity=updated["total_quantity"],
        created_at=updated["created_at"],
        updated_at=updated["updated_at"],
    )


@router.delete("/{component_id}")
def delete_component(
    component_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM components WHERE id = %s RETURNING id;", (component_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Component not found")

    conn.commit()
    cursor.close()
    conn.close()

    return {"detail": "Component deleted"}
