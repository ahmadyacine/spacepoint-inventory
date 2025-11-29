# backend/routers/auth.py
from fastapi import APIRouter, HTTPException
from uuid import uuid4
from ..schemas import LoginRequest, LoginResponse
from ..deps import fake_tokens
from ..database import get_connection
router = APIRouter(prefix="/auth", tags=["auth"])
@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check user in database - UPDATED to include instructor_id
    cursor.execute(
        "SELECT id, username, password, full_name, role, instructor_id FROM users WHERE username = %s;",
        (data.username,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=400, detail="Invalid username or password")
    token = str(uuid4())
    fake_tokens[token] = {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "instructor_id": user["instructor_id"],
    }
    return LoginResponse(
        token=token,
        username=user["username"],
        full_name=user["full_name"],
        role=user["role"],
        instructor_id=user["instructor_id"],
        id=user["id"],
    )
