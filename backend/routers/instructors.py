# backend/routers/instructors.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from ..database import get_connection
from ..schemas import InstructorCreate, InstructorOut
from ..deps import require_role

router = APIRouter(prefix="/instructors", tags=["instructors"])


def row_to_instructor(row) -> InstructorOut:
    return InstructorOut(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        phone=row["phone"],
        location=row["location"],
        user_id=row.get("user_id"),
    )


@router.post("/", response_model=InstructorOut)
def create_instructor(
    instructor: InstructorCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # If user_id is provided, check if it exists
    if instructor.user_id:
        cursor.execute("SELECT id FROM users WHERE id = %s;", (instructor.user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="User not found")

    cursor.execute(
        """
        INSERT INTO instructors (name, email, phone, location, user_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, email, phone, location, user_id
        """,
        (
            instructor.name,
            instructor.email,
            instructor.phone,
            instructor.location,
            instructor.user_id,
        )
    )
    row = cursor.fetchone()
    new_instructor_id = row["id"]

    # If user_id is provided, update the user's instructor_id
    if instructor.user_id:
        cursor.execute(
            "UPDATE users SET instructor_id = %s WHERE id = %s;",
            (new_instructor_id, instructor.user_id)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return row_to_instructor(row)


@router.get("/", response_model=List[InstructorOut])
def list_instructors(
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, phone, location, user_id FROM instructors;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row_to_instructor(r) for r in rows]

@router.get("/{instructor_id}", response_model=InstructorOut)
def get_instructor(
    instructor_id: int,
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, phone, location, user_id FROM instructors WHERE id = %s;",
        (instructor_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    return row_to_instructor(row)

@router.put("/{instructor_id}", response_model=InstructorOut)
def update_instructor(
    instructor_id: int,
    instructor: InstructorCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if instructor exists
    cursor.execute("SELECT id FROM instructors WHERE id = %s;", (instructor_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    # Update instructor with RETURNING
    cursor.execute(
        """
        UPDATE instructors 
        SET name = %s, email = %s, phone = %s, location = %s, user_id = %s
        WHERE id = %s
        RETURNING id, name, email, phone, location, user_id
        """,
        (
            instructor.name,
            instructor.email,
            instructor.phone,
            instructor.location,
            instructor.user_id,
            instructor_id
        )
    )
    row = cursor.fetchone()
    
    # If user_id is provided, update the user's instructor_id
    if instructor.user_id:
        cursor.execute(
            "UPDATE users SET instructor_id = %s WHERE id = %s;",
            (instructor_id, instructor.user_id)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return row_to_instructor(row)

@router.delete("/{instructor_id}")
def delete_instructor(
    instructor_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if instructor exists
    cursor.execute("SELECT id, name FROM instructors WHERE id = %s;", (instructor_id,))
    instructor = cursor.fetchone()
    
    if not instructor:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    # Delete instructor
    cursor.execute("DELETE FROM instructors WHERE id = %s;", (instructor_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"Instructor {instructor['name']} deleted successfully"}