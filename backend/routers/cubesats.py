# backend/routers/cubesats.py
from fastapi import APIRouter, Depends, Response, HTTPException
from typing import List
import io
import pandas as pd
from ..database import get_connection
from ..schemas import CubesatCreate, CubesatOut
from ..deps import require_role

router = APIRouter(prefix="/cubesats", tags=["cubesats"])

# Required counts for a "complete" CubeSat kit
REQUIRED_COUNTS = {
    # Existing items
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

    # New boards
    "cdhs_board": 1,
    "eps_board": 1,
    "adcs_board": 1,

    # New electronics
    "esp32_cam": 1,
    "esp32": 1,
    "magnetorquer": 1,
    "buck_converter_module": 1,
    "li_ion_battery": 1,
    "pin_socket": 4,

    # New mechanical
    "m3_screws": 20,
    "m3_hex_nut": 4,
    "m3_9_6mm_brass_standoff": 4,
    "m3_10mm_brass_standoff": 4,
    "m3_10_6mm_brass_standoff": 4,
    "m3_20_6mm_brass_standoff": 12,
}


def calculate_missing_items(c: CubesatCreate) -> str:
    """
    Check each part in REQUIRED_COUNTS and return a multi-line string
    like:
        structures: missing 2
        esp32_cam: missing 1
    or empty string if everything is complete.
    """
    missing = []
    for field, required in REQUIRED_COUNTS.items():
        count = getattr(c, field)
        if count < required:
            missing.append(f"{field}: missing {required - count}")
    return "\n".join(missing) if missing else ""


def row_to_cubesat(row) -> CubesatOut:
    """
    Convert a DB row (RealDictCursor) into a CubesatOut Pydantic model.
    Handles name differences between DB columns and Pydantic fields.
    """
    return CubesatOut(
        id=row["id"],
        name=row["name"],
        status=row["status"],
        location=row["location"],
        delivered_date=row["delivereddate"],
        instructor_id=row["instructorid"],
        instructor_name=row.get("instructor_name"),  
        instructor_phone=row.get("instructor_phone"),           # 👈 NEW
        instructor_location=row.get("instructor_location"),     # 👈 NEW

        # Existing items
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

        # New items
        cdhs_board=row["cdhs_board"],
        eps_board=row["eps_board"],
        adcs_board=row["adcs_board"],
        esp32_cam=row["esp32_cam"],
        esp32=row["esp32"],
        magnetorquer=row["magnetorquer"],
        buck_converter_module=row["buck_converter_module"],
        li_ion_battery=row["li_ion_battery"],
        pin_socket=row["pin_socket"],
        m3_screws=row["m3_screws"],
        m3_hex_nut=row["m3_hex_nut"],
        m3_9_6mm_brass_standoff=row["m3_9_6mm_brass_standoff"],
        m3_10mm_brass_standoff=row["m3_10mm_brass_standoff"],
        m3_10_6mm_brass_standoff=row["m3_10_6mm_brass_standoff"],
        m3_20_6mm_brass_standoff=row["m3_20_6mm_brass_standoff"],

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

    # INSERT with RETURNING for PostgreSQL
    cursor.execute(
        """
        INSERT INTO cubesats (
            name, status, location, delivereddate, instructorid,
            structures, currentsensors, tempsensors, fram, sdcard,
            reactionwheel, mpu, gps, motordriver, phillipsscrewdriver,
            screwgauge3d, standofftool3d,
            cdhs_board, eps_board, adcs_board,
            esp32_cam, esp32, magnetorquer, buck_converter_module,
            li_ion_battery, pin_socket,
            m3_screws, m3_hex_nut,
            m3_9_6mm_brass_standoff, m3_10mm_brass_standoff,
            m3_10_6mm_brass_standoff, m3_20_6mm_brass_standoff,
            iscomplete, missingitems, received_date
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s
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
            cubesat.cdhs_board,
            cubesat.eps_board,
            cubesat.adcs_board,
            cubesat.esp32_cam,
            cubesat.esp32,
            cubesat.magnetorquer,
            cubesat.buck_converter_module,
            cubesat.li_ion_battery,
            cubesat.pin_socket,
            cubesat.m3_screws,
            cubesat.m3_hex_nut,
            cubesat.m3_9_6mm_brass_standoff,
            cubesat.m3_10mm_brass_standoff,
            cubesat.m3_10_6mm_brass_standoff,
            cubesat.m3_20_6mm_brass_standoff,
            is_complete,
            missing_str if missing_str else None,
            cubesat.delivered_date,  # received_date initially same as delivered_date (or None)
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

    # in list_cubesats()

    if current_user["role"] == "instructor":
        cursor.execute(
            """
            SELECT 
                c.*,
                i.name AS instructor_name,
            i.phone AS instructor_phone,
            i.location AS instructor_location
        FROM cubesats c
        LEFT JOIN instructors i
            ON c.instructorid = i.id
        WHERE c.instructorid = %s
          AND c.is_received = TRUE
        ORDER BY c.id DESC;
        """,
        (current_user["instructor_id"],),
    )
    else:
        cursor.execute(
            """
            SELECT 
                c.*,
                i.name AS instructor_name,
                i.phone AS instructor_phone,
                i.location AS instructor_location
            FROM cubesats c
            LEFT JOIN instructors i
                ON c.instructorid = i.id
            ORDER BY c.id DESC;
            """
        )

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return [row_to_cubesat(r) for r in rows]

@router.get("/{cubesat_id}", response_model=CubesatOut)
def get_cubesat(
    cubesat_id: int,
    current_user = Depends(require_role("admin", "operations", "instructor")),
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            c.*,
            i.name AS instructor_name,
            i.phone AS instructor_phone,
            i.location AS instructor_location
        FROM cubesats c
        LEFT JOIN instructors i
            ON c.instructorid = i.id
        WHERE c.id = %s;
        """,
        (cubesat_id,),
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

    # Update with RETURNING
    cursor.execute(
        """
        UPDATE cubesats 
        SET name = %s, status = %s, location = %s, delivereddate = %s, instructorid = %s,
            structures = %s, currentsensors = %s, tempsensors = %s, fram = %s, sdcard = %s,
            reactionwheel = %s, mpu = %s, gps = %s, motordriver = %s, phillipsscrewdriver = %s,
            screwgauge3d = %s, standofftool3d = %s,
            cdhs_board = %s, eps_board = %s, adcs_board = %s,
            esp32_cam = %s, esp32 = %s, magnetorquer = %s, buck_converter_module = %s,
            li_ion_battery = %s, pin_socket = %s,
            m3_screws = %s, m3_hex_nut = %s,
            m3_9_6mm_brass_standoff = %s, m3_10mm_brass_standoff = %s,
            m3_10_6mm_brass_standoff = %s, m3_20_6mm_brass_standoff = %s,
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
            cubesat.cdhs_board,
            cubesat.eps_board,
            cubesat.adcs_board,
            cubesat.esp32_cam,
            cubesat.esp32,
            cubesat.magnetorquer,
            cubesat.buck_converter_module,
            cubesat.li_ion_battery,
            cubesat.pin_socket,
            cubesat.m3_screws,
            cubesat.m3_hex_nut,
            cubesat.m3_9_6mm_brass_standoff,
            cubesat.m3_10mm_brass_standoff,
            cubesat.m3_10_6mm_brass_standoff,
            cubesat.m3_20_6mm_brass_standoff,
            is_complete,
            missing_str if missing_str else None,
            cubesat_id,
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
                detail=(
                    "Cannot delete Cubesat because it has associated receipts or other data. "
                    "Please delete the associated data first."
                ),
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
            raise HTTPException(
                status_code=404, detail="No cubesats data found to export"
            )

        cubesats_data = []
        for row in rows:
            cubesat_dict = {
                "ID": row["id"],
                "Name": row["name"] or "",
                "Status": row["status"] or "",
                "Location": row["location"] or "",
                "Delivered Date": row["delivereddate"].strftime("%Y-%m-%d")
                if row["delivereddate"]
                else "",
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

                "CDHS Board": row.get("cdhs_board", 0) or 0,
                "EPS Board": row.get("eps_board", 0) or 0,
                "ADCS Board": row.get("adcs_board", 0) or 0,
                "ESP32-CAM": row.get("esp32_cam", 0) or 0,
                "ESP32": row.get("esp32", 0) or 0,
                "Magnetorquer": row.get("magnetorquer", 0) or 0,
                "Buck Converter Module": row.get("buck_converter_module", 0) or 0,
                "Li-ion Battery": row.get("li_ion_battery", 0) or 0,
                "Pin Socket": row.get("pin_socket", 0) or 0,
                "M3 Screws": row.get("m3_screws", 0) or 0,
                "M3 Hex Nut": row.get("m3_hex_nut", 0) or 0,
                "M3 9+6mm Brass Standoff": row.get("m3_9_6mm_brass_standoff", 0) or 0,
                "M3 10mm Brass Standoff": row.get("m3_10mm_brass_standoff", 0) or 0,
                "M3 10+6mm Brass Standoff": row.get("m3_10_6mm_brass_standoff", 0) or 0,
                "M3 20+6mm Brass Standoff": row.get("m3_20_6mm_brass_standoff", 0) or 0,

                "Is Complete": "Yes" if row["iscomplete"] else "No",
                "Missing Items": row["missingitems"] or "None",
                "Is Received": "Yes" if row.get("is_received") else "No",
                "Received Date": row["received_date"].strftime("%Y-%m-%d")
                if row.get("received_date")
                else "",
            }
            cubesats_data.append(cubesat_dict)

        # Create DataFrame
        df = pd.DataFrame(cubesats_data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Cubesats Inventory", index=False)

            # Auto-adjust column widths
            worksheet = writer.sheets["Cubesats Inventory"]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except Exception:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Return Excel file
        return Response(
            content=output.getvalue(),
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": "attachment; filename=cubesats_inventory.xlsx",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating Excel file: {str(e)}"
        )
