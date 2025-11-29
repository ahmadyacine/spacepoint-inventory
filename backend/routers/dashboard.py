# backend/routers/dashboard.py
from typing import Dict
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_connection
from ..deps import require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Add this to backend/routers/cubesats.py or create a new dashboard.py file

@router.get("/dashboard/statistics")
def get_dashboard_stats(current_user=Depends(require_role("admin", "operations"))):
    """
    Temporary dashboard statistics endpoint
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get cubesats counts by status
        cursor.execute("""
            SELECT 
                Status,
                COUNT(*) as count
            FROM Cubesats 
            GROUP BY Status
        """)
        status_counts = cursor.fetchall()
        
        # Get complete/incomplete counts
        cursor.execute("""
            SELECT 
                IsComplete,
                COUNT(*) as count
            FROM Cubesats 
            GROUP BY IsComplete
        """)
        completion_counts = cursor.fetchall()
        
        # Get total instructors
        cursor.execute("SELECT COUNT(*) as count FROM Instructors")
        instructors_count = cursor.fetchone()
        
        # Convert to dictionary format
        status_dict = {row.Status: row.count for row in status_counts}
        complete_count = next((row.count for row in completion_counts if row.IsComplete == 1), 0)
        incomplete_count = next((row.count for row in completion_counts if row.IsComplete == 0), 0)
        
        return {
            "cubesats": {
                "total": sum(status_dict.values()),
                "working": status_dict.get('working', 0),
                "damaged": status_dict.get('damaged', 0),
                "repairing": status_dict.get('repeating', 0),
                "complete": complete_count,
                "incomplete": incomplete_count
            },
            "instructors": {
                "total": instructors_count.count
            }
        }
        
    except Exception as e:
        print(f"Error in dashboard stats: {e}")
        return {
            "cubesats": {
                "total": 0,
                "working": 0,
                "damaged": 0,
                "repairing": 0,
                "complete": 0,
                "incomplete": 0
            },
            "instructors": {
                "total": 0
            }
        }
    finally:
        cursor.close()
        conn.close()