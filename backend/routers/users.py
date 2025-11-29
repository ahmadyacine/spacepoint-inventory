# backend/routers/users.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..schemas import UserCreate, UserOut
from ..deps import require_role

router = APIRouter(prefix="/users", tags=["users"])


def row_to_user(row) -> UserOut:
    return UserOut(
        id=row["id"],
        username=row["username"],
        full_name=row["full_name"],
        role=row["role"],
        created_at=row["created_at"],
    )


@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    current_user=Depends(require_role("admin")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT id FROM users WHERE username = %s;", (user.username,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    cursor.execute(
        """
        INSERT INTO users (username, password, full_name, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id, username, full_name, role, created_at
        """,
        (
            user.username,
            user.password,
            user.full_name,
            user.role,
        )
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_user(row)


@router.get("/", response_model=List[UserOut])
def list_users(
    current_user=Depends(require_role("admin")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name, role, created_at FROM users;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row_to_user(r) for r in rows]


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    current_user=Depends(require_role("admin")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, full_name, role, created_at FROM users WHERE id = %s;",
        (user_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    return row_to_user(row)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user: UserCreate,
    current_user=Depends(require_role("admin")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if username already exists (excluding current user)
    cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s;", (user.username, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Update user
    cursor.execute(
        """
        UPDATE users 
        SET username = %s, password = %s, full_name = %s, role = %s
        WHERE id = %s
        RETURNING id, username, full_name, role, created_at
        """,
        (
            user.username,
            user.password,
            user.full_name,
            user.role,
            user_id
        )
    )
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_user(row)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user=Depends(require_role("admin")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id, username FROM users WHERE id = %s;", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if current_user["username"] == user["username"]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Delete user
    cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"User {user['username']} deleted successfully"}