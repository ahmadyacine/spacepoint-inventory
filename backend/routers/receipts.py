from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..models import ReceiptStatus, NotificationType
from ..deps import require_role
from pydantic import BaseModel
from typing import Dict, Any
import json

router = APIRouter(prefix="/receipts", tags=["receipts"])

class ReceiptCreate(BaseModel):
    cubesat_id: int
    items: Dict[str, int]

from .websockets import manager

# ... imports ...

@router.post("/")
async def create_receipt(
    receipt_data: ReceiptCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get instructor_id from cubesat
        cursor.execute("SELECT instructorid, name FROM cubesats WHERE id = %s", (receipt_data.cubesat_id,))
        cubesat = cursor.fetchone()
        
        if not cubesat:
            raise HTTPException(status_code=404, detail="Cubesat not found")
            
        instructor_id = cubesat['instructorid']
        if not instructor_id:
            raise HTTPException(status_code=400, detail="Cubesat has no assigned instructor")

        # Get instructor's user_id for notification
        cursor.execute("SELECT user_id, name FROM instructors WHERE id = %s", (instructor_id,))
        instructor = cursor.fetchone()
        
        if not instructor or not instructor['user_id']:
            raise HTTPException(status_code=400, detail="Instructor has no linked user account for notifications")

        # Create Receipt
        items_json = json.dumps(receipt_data.items)
        cursor.execute(
            """
            INSERT INTO receipts (cubesat_id, instructor_id, items, status, generated_by, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id, created_at
            """,
            (receipt_data.cubesat_id, instructor_id, items_json, ReceiptStatus.pending, current_user['id'])
        )
        receipt_row = cursor.fetchone()
        receipt_id = receipt_row['id']
        created_at = receipt_row['created_at']

        # Create Notification
        cursor.execute(
            """
            INSERT INTO notifications (user_id, title, message, type, is_read, created_at, related_entity_id, related_entity_type)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
            """,
            (
                instructor['user_id'],
                "Equipment Receipt Approval Required",
                f"Please approve the receipt for equipment issued to CubeSat {cubesat['name']}.",
                NotificationType.receipt_approval,
                False,
                receipt_id,
                "receipt"
            )
        )

        conn.commit()

        # Send WebSocket notification
        await manager.send_personal_message(
            {
                "type": "new_receipt",
                "receipt": {
                    "id": receipt_id,
                    "cubesat_name": cubesat['name'],
                    "created_at": created_at.isoformat(),
                    "status": ReceiptStatus.pending
                },
                "notification": {
                    "title": "Equipment Receipt Approval Required",
                    "message": f"Please approve the receipt for equipment issued to CubeSat {cubesat['name']}."
                }
            },
            instructor['user_id']
        )

        return {"message": "Receipt created and sent for approval", "receipt_id": receipt_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/{receipt_id}")
def get_receipt(
    receipt_id: int,
    current_user=Depends(require_role("instructor", "admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT r.*, c.name as cubesat_name, i.name as instructor_name
            FROM receipts r
            JOIN cubesats c ON r.cubesat_id = c.id
            JOIN instructors i ON r.instructor_id = i.id
            WHERE r.id = %s
            """,
            (receipt_id,)
        )
        receipt = cursor.fetchone()
        
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
            
        return receipt
    finally:
        cursor.close()
        conn.close()

@router.put("/{receipt_id}/approve")
def approve_receipt(
    receipt_id: int,
    current_user=Depends(require_role("instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verify receipt exists and belongs to instructor
        cursor.execute(
            """
            SELECT r.*, i.user_id 
            FROM receipts r
            JOIN instructors i ON r.instructor_id = i.id
            WHERE r.id = %s
            """, 
            (receipt_id,)
        )
        receipt = cursor.fetchone()
        
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
            
        # Check if the current user is the linked instructor
        if receipt['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to approve this receipt")

        # Update receipt status
        cursor.execute(
            "UPDATE receipts SET status = %s WHERE id = %s",
            (ReceiptStatus.approved, receipt_id)
        )

        # Mark notification as read
        cursor.execute(
            """
            UPDATE notifications 
            SET is_read = true 
            WHERE related_entity_id = %s AND related_entity_type = 'receipt' AND user_id = %s
            """,
            (receipt_id, current_user['id'])
        )

        # Update CubeSat is_received status and received date
        cursor.execute(
            "UPDATE cubesats SET is_received = TRUE, received_date = CURRENT_DATE WHERE id = %s",
            (receipt['cubesat_id'],)
        )

        conn.commit()
        return {"message": "Receipt approved successfully"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.get("/")
def list_receipts(
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            SELECT r.*, c.name as cubesat_name, i.name as instructor_name
            FROM receipts r
            JOIN cubesats c ON r.cubesat_id = c.id
            JOIN instructors i ON r.instructor_id = i.id
            ORDER BY r.created_at DESC
            """
        )
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()

@router.delete("/{receipt_id}")
def delete_receipt(
    receipt_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if receipt exists
        cursor.execute("SELECT id FROM receipts WHERE id = %s", (receipt_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Receipt not found")

        # Delete associated notifications first (optional, but good practice if no cascade)
        cursor.execute("DELETE FROM notifications WHERE related_entity_id = %s AND related_entity_type = 'receipt'", (receipt_id,))

        # Delete receipt
        cursor.execute("DELETE FROM receipts WHERE id = %s", (receipt_id,))
        
        conn.commit()
        return {"message": "Receipt deleted successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
