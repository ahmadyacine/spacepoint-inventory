from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..deps import get_current_user
from typing import List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["notifications"])

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    related_entity_id: int | None
    related_entity_type: str | None

@router.get("/")
def list_notifications(
    current_user=Depends(get_current_user),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT * FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC
        """,
        (current_user['id'],)
    )
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return rows

@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user=Depends(get_current_user),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE notifications SET is_read = true WHERE id = %s AND user_id = %s",
        (notification_id, current_user['id'])
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"message": "Notification marked as read"}
