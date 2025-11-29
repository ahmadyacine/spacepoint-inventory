# backend/routers/cubesats.py
from fastapi import APIRouter, Depends, Response, HTTPException
from typing import List
import io
import pandas as pd
from ..database import get_connection
from ..schemas import CubesatCreate, CubesatOut
from ..deps import require_role

router = APIRouter(prefix="/cubesats", tags=["cubesats"])

REQUIRED_COUNTS = {
    "structures": 6,
    "current_sensors": 2,
    "temp_sensors": 1,
    "fram": 1,
    "sd_card": 1,
    "reaction_wheel": 1,
    "mpu": 1,
    "gps": 1,
    "motor_driver": 1,
    "phillips_screwdriver": 1,
    "screw_gauge_3d": 1,
    "standoff_tool_3d": 1,
    "m3_10mm": 1,
    "m3_10mm_thread": 1,
    "m3_9mm_thread": 1,
    "m3_20mm_thread": 1,
    "m3_6mm": 1,
}


def calculate_missing_items(c: CubesatCreate) -> str:
    missing = []
    for field, required in REQUIRED_COUNTS.items():
        count = getattr(c, field)
        if count < required:
            missing.append(f"{field}: missing {required - count}")
    return "\n".join(missing) if missing else ""


def row_to_cubesat(row) -> CubesatOut:
    return CubesatOut(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        location=row["location"],
        delivered_date=row["delivereddate"],
        instructor_id=row["instructorid"],
        structures=row["structures"],
        current_sensors=row["currentsensors"],
        temp_sensors=row["tempsensors"],
        fram=row["fram"],
        sd_card=row["sdcard"],
        reaction_wheel=row["reactionwheel"],
        mpu=row["mpu"],
        gps=row["gps"],
        motor_driver=row["motordriver"],
        phillips_screwdriver=row["phillipsscrewdriver"],
        screw_gauge_3d=row["screwgauge3d"],
        standoff_tool_3d=row["standofftool3d"],
        m3_10mm=row["m3_10mm"],
        m3_10mm_thread=row["m3_10mm_thread"],
        m3_9mm_thread=row["m3_9mm_thread"],
        m3_20mm_thread=row["m3_20mm_thread"],
        m3_6mm=row["m3_6mm"],
        is_complete=bool(row["iscomplete"]),
        missing_items=row["missingitems"],
        is_received=bool(row.get("is_received", False)),
        received_date=row.get("received_date"),
    )


@router.post("/", response_model=CubesatOut)
def create_cubesat(
    cubesat: CubesatCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    missing_str = calculate_missing_items(cubesat)
    is_complete = False if missing_str else True

    conn = get_connection()
    cursor = conn.cursor()

    # 1) INSERT with RETURNING for PostgreSQL
    cursor.execute(
        """
        INSERT INTO cubesats (
            name, status, location, delivereddate, instructorid,
            structures, currentsensors, tempsensors, fram, sdcard,
            reactionwheel, mpu, gps, motordriver, phillipsscrewdriver,
            screwgauge3d, standofftool3d, m3_10mm, m3_10mm_thread,
            m3_9mm_thread, m3_20mm_thread, m3_6mm,
            iscomplete, missingitems, received_date
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        RETURNING *
        """,
        (
            cubesat.name,
            cubesat.status,
            cubesat.location,
            cubesat.delivered_date,
            cubesat.instructor_id,
            cubesat.structures,
            cubesat.current_sensors,
            cubesat.temp_sensors,
            cubesat.fram,
            cubesat.sd_card,
            cubesat.reaction_wheel,
            cubesat.mpu,
            cubesat.gps,
            cubesat.motor_driver,
            cubesat.phillips_screwdriver,
            cubesat.screw_gauge_3d,
            cubesat.standoff_tool_3d,
            cubesat.m3_10mm,
            cubesat.m3_10mm_thread,
            cubesat.m3_9mm_thread,
            cubesat.m3_20mm_thread,
            cubesat.m3_6mm,
            is_complete,
            missing_str if missing_str else None,
            cubesat.delivered_date, # received_date initially same as delivered_date
        )
    )
    
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_cubesat(row)


@router.get("/", response_model=List[CubesatOut])
def list_cubesats(
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    if current_user["role"] == "instructor":
        cursor.execute("SELECT * FROM cubesats WHERE instructorid = %s AND is_received = TRUE;", (current_user["instructor_id"],))
    else:
        cursor.execute("SELECT * FROM cubesats;")
        
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row_to_cubesat(r) for r in rows]


@router.get("/{cubesat_id}", response_model=CubesatOut)
def get_cubesat(
    cubesat_id: int,
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cubesats WHERE id = %s;",
        (cubesat_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Cubesat not found")
    
    return row_to_cubesat(row)


@router.put("/{cubesat_id}", response_model=CubesatOut)
def update_cubesat(
    cubesat_id: int,
    cubesat: CubesatCreate,
    current_user=Depends(require_role("admin", "operations")),
):
    missing_str = calculate_missing_items(cubesat)
    is_complete = False if missing_str else True

    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if cubesat exists
    cursor.execute("SELECT id FROM cubesats WHERE id = %s;", (cubesat_id,))
    if not cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Cubesat not found")
    
    # Update cubesat with RETURNING
    cursor.execute(
        """
        UPDATE cubesats 
        SET name = %s, status = %s, location = %s, delivereddate = %s, instructorid = %s,
            structures = %s, currentsensors = %s, tempsensors = %s, fram = %s, sdcard = %s,
            reactionwheel = %s, mpu = %s, gps = %s, motordriver = %s, phillipsscrewdriver = %s,
            screwgauge3d = %s, standofftool3d = %s, m3_10mm = %s, m3_10mm_thread = %s,
            m3_9mm_thread = %s, m3_20mm_thread = %s, m3_6mm = %s,
            iscomplete = %s, missingitems = %s
        WHERE id = %s
        RETURNING *
        """,
        (
            cubesat.name,
            cubesat.status,
            cubesat.location,
            cubesat.delivered_date,
            cubesat.instructor_id,
            cubesat.structures,
            cubesat.current_sensors,
            cubesat.temp_sensors,
            cubesat.fram,
            cubesat.sd_card,
            cubesat.reaction_wheel,
            cubesat.mpu,
            cubesat.gps,
            cubesat.motor_driver,
            cubesat.phillips_screwdriver,
            cubesat.screw_gauge_3d,
            cubesat.standoff_tool_3d,
            cubesat.m3_10mm,
            cubesat.m3_10mm_thread,
            cubesat.m3_9mm_thread,
            cubesat.m3_20mm_thread,
            cubesat.m3_6mm,
            is_complete,
            missing_str if missing_str else None,
            cubesat_id
        )
    )
    
    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    return row_to_cubesat(row)


@router.delete("/{cubesat_id}")
def delete_cubesat(
    cubesat_id: int,
    current_user=Depends(require_role("admin", "operations")),
):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if cubesat exists
    cursor.execute("SELECT id, name FROM cubesats WHERE id = %s;", (cubesat_id,))
    cubesat = cursor.fetchone()
    
    if not cubesat:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Cubesat not found")
    
    try:
        # Delete cubesat
        cursor.execute("DELETE FROM cubesats WHERE id = %s;", (cubesat_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        if "foreign key constraint" in str(e).lower():
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete Cubesat because it has associated receipts or other data. Please delete the associated data first."
            )
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    cursor.close()
    conn.close()

    return {"message": f"Cubesat {cubesat['name']} deleted successfully"}


@router.get("/export/excel")
def export_cubesats_excel(
    current_user=Depends(require_role("admin", "operations", "instructor")),
):
    """
    Export all cubesats data to Excel format
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cubesats;")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail="No cubesats data found to export")

        # Convert to list of dictionaries
        cubesats_data = []
        for row in rows:
            cubesat_dict = {
                "ID": row["id"],
                "Name": row["name"] or "",
                "Status": row["status"] or "",
                "Location": row["location"] or "",
                "Delivered Date": row["delivereddate"].strftime("%Y-%m-%d") if row["delivereddate"] else "",
                "Instructor ID": row["instructorid"] or "",
                "Structures": row["structures"] or 0,
                "Current Sensors": row["currentsensors"] or 0,
                "Temperature Sensors": row["tempsensors"] or 0,
                "FRAM": row["fram"] or 0,
                "SD Card": row["sdcard"] or 0,
                "Reaction Wheel": row["reactionwheel"] or 0,
                "MPU": row["mpu"] or 0,
                "GPS": row["gps"] or 0,
                "Motor Driver": row["motordriver"] or 0,
                "Phillips Screwdriver": row["phillipsscrewdriver"] or 0,
                "Screw Gauge 3D": row["screwgauge3d"] or 0,
                "Standoff Tool 3D": row["standofftool3d"] or 0,
                "M3 10mm": row["m3_10mm"] or 0,
                "M3 10mm Thread": row["m3_10mm_thread"] or 0,
                "M3 9mm Thread": row["m3_9mm_thread"] or 0,
                "M3 20mm Thread": row["m3_20mm_thread"] or 0,
                "M3 6mm": row["m3_6mm"] or 0,
                "Is Complete": "Yes" if row["iscomplete"] else "No",
                "Missing Items": row["missingitems"] or "None",
            }
            cubesats_data.append(cubesat_dict)

        # Create DataFrame
        df = pd.DataFrame(cubesats_data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Cubesats Inventory', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Cubesats Inventory']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        
        # Return Excel file
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": "attachment; filename=cubesats_inventory.xlsx",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel file: {str(e)}")