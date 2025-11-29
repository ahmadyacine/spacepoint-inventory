from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..schemas import WorkshopCreate, WorkshopOut
from ..deps import require_role

router = APIRouter(prefix="/workshops", tags=["workshops"])

def row_to_workshop(row) -> WorkshopOut:
    return WorkshopOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        workshop_type=row["workshop_type"],
        status=row["status"],
        location=row["location"],
        instructor_id=row["instructor_id"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        max_participants=row["max_participants"],
        current_participants=row["current_participants"],
        requirements=row["requirements"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/", response_model=WorkshopOut)
def create_workshop(
    workshop: WorkshopCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        INSERT INTO workshops (
            title, description, workshop_type, status, location, instructor_id,
            start_date, end_date, max_participants, current_participants,
            requirements, notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            workshop.title,
            workshop.description,
            workshop.workshop_type,
            workshop.status,
            workshop.location,
            workshop.instructor_id,
            workshop.start_date,
            workshop.end_date,
            workshop.max_participants,
            workshop.current_participants,
            workshop.requirements,
            workshop.notes,
        )
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_workshop(row)


@router.get("/", response_model=List[WorkshopOut])
def list_workshops(
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    if current_user["role"] == "instructor":
        cursor.execute("SELECT * FROM workshops WHERE instructor_id = %s ORDER BY start_date;", (current_user["instructor_id"],))
    else:
        cursor.execute("SELECT * FROM workshops ORDER BY start_date;")
        
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row_to_workshop(r) for r in rows]


@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(
    workshop_id: int,
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM workshops WHERE id = %s;",
        (workshop_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    return row_to_workshop(row)


@router.put("/{workshop_id}", response_model=WorkshopOut)
def update_workshop(
    workshop_id: int,
    workshop: WorkshopCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if workshop exists
    cursor.execute("SELECT id FROM workshops WHERE id = %s;", (workshop_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    # Update workshop
    cursor.execute(
        """
        UPDATE workshops 
        SET title = %s, description = %s, workshop_type = %s, status = %s,
            location = %s, instructor_id = %s, start_date = %s, end_date = %s,
            max_participants = %s, current_participants = %s, requirements = %s,
            notes = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING *
        """,
        (
            workshop.title,
            workshop.description,
            workshop.workshop_type,
            workshop.status,
            workshop.location,
            workshop.instructor_id,
            workshop.start_date,
            workshop.end_date,
            workshop.max_participants,
            workshop.current_participants,
            workshop.requirements,
            workshop.notes,
            workshop_id
        )
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_workshop(row)


@router.delete("/{workshop_id}")
def delete_workshop(
    workshop_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if workshop exists
    cursor.execute("SELECT id, title FROM workshops WHERE id = %s;", (workshop_id,))
    workshop = cursor.fetchone()
    
    if not workshop:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Workshop not found")
    
    # Delete workshop
    cursor.execute("DELETE FROM workshops WHERE id = %s;", (workshop_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"Workshop '{workshop['title']}' deleted successfully"}