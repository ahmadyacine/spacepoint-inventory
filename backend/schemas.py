# backend/schemas.py
from datetime import date, datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    id: int
    username: str
    full_name: str
    role: str
    instructor_id: Optional[int] = None


class InstructorCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    user_id: Optional[int] = None


class InstructorOut(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    user_id: Optional[int]


class CubesatCreate(BaseModel):
    name: str
    status: str
    location: Optional[str] = None
    delivered_date: Optional[date] = None
    instructor_id: Optional[int] = None

    # Existing items
    structures: int = 0
    current_sensors: int = 0
    temp_sensors: int = 0
    fram: int = 0
    sd_card: int = 0
    reaction_wheel: int = 0
    mpu: int = 0
    gps: int = 0
    motor_driver: int = 0
    phillips_screwdriver: int = 0
    screw_gauge_3d: int = 0
    standoff_tool_3d: int = 0

    # NEW items
    cdhs_board: int = 0
    eps_board: int = 0
    adcs_board: int = 0
    esp32_cam: int = 0
    esp32: int = 0
    magnetorquer: int = 0
    buck_converter_module: int = 0
    li_ion_battery: int = 0
    pin_socket: int = 0
    m3_screws: int = 0
    m3_hex_nut: int = 0
    m3_9_6mm_brass_standoff: int = 0
    m3_10mm_brass_standoff: int = 0
    m3_10_6mm_brass_standoff: int = 0
    m3_20_6mm_brass_standoff: int = 0


class CubesatOut(BaseModel):
    id: int
    name: str
    status: str
    location: Optional[str]
    delivered_date: Optional[date]
    instructor_id: Optional[int]
    instructor_name: Optional[str] = None
    instructor_phone: Optional[str] = None      # 👈 NEW
    instructor_location: Optional[str] = None   # 👈 NEW

    # Existing items
    structures: int
    current_sensors: int
    temp_sensors: int
    fram: int
    sd_card: int
    reaction_wheel: int
    mpu: int
    gps: int
    motor_driver: int
    phillips_screwdriver: int
    screw_gauge_3d: int
    standoff_tool_3d: int

    # NEW items
    cdhs_board: int
    eps_board: int
    adcs_board: int
    esp32_cam: int
    esp32: int
    magnetorquer: int
    buck_converter_module: int
    li_ion_battery: int
    pin_socket: int
    m3_screws: int
    m3_hex_nut: int
    m3_9_6mm_brass_standoff: int
    m3_10mm_brass_standoff: int
    m3_10_6mm_brass_standoff: int
    m3_20_6mm_brass_standoff: int

    is_complete: bool
    missing_items: Optional[str]
    is_received: bool = False
    received_date: Optional[date] = None



class UserBase(BaseModel):
    username: str
    full_name: str
    role: str


class UserCreate(UserBase):
    # password required عند إنشاء المستخدم
    password: str


class UserUpdate(UserBase):
    # password اختياري عند التحديث
    password: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    created_at: datetime


class WorkshopBase(BaseModel):
    title: str
    description: Optional[str] = None
    workshop_type: str
    status: str
    location: Optional[str] = None
    start_date: datetime
    end_date: datetime
    max_participants: Optional[int] = None
    current_participants: int = 0
    requirements: Optional[str] = None
    notes: Optional[str] = None

    # NEW
    lead_instructor_id: Optional[int] = None                 # main instructor
    instructor_ids: Optional[List[int]] = None               # list of assigned instructors


class WorkshopCreate(WorkshopBase):
    pass


class WorkshopOut(WorkshopBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # Keep legacy field for compatibility if you want
    instructor_id: Optional[int] = None                      # alias/legacy
    instructors: List[int] = []                              # same as instructor_ids but always a list

    class Config:
        orm_mode = True

class SessionLogCreate(BaseModel):
    cubesat_id: int
    instructor_id: int

    # Existing items
    structures: int = 0
    current_sensors: int = 0
    temp_sensors: int = 0
    fram: int = 0
    sd_card: int = 0
    reaction_wheel: int = 0
    mpu: int = 0
    gps: int = 0
    motor_driver: int = 0
    phillips_screwdriver: int = 0
    screw_gauge_3d: int = 0
    standoff_tool_3d: int = 0


    # NEW items
    cdhs_board: int = 0
    eps_board: int = 0
    adcs_board: int = 0
    esp32_cam: int = 0
    esp32: int = 0
    magnetorquer: int = 0
    buck_converter_module: int = 0
    li_ion_battery: int = 0
    pin_socket: int = 0
    m3_screws: int = 0
    m3_hex_nut: int = 0
    m3_9_6mm_brass_standoff: int = 0
    m3_10mm_brass_standoff: int = 0
    m3_10_6mm_brass_standoff: int = 0
    m3_20_6mm_brass_standoff: int = 0



class SessionLogOut(BaseModel):
    id: int
    cubesat_id: int
    instructor_id: int
    missing_items: Optional[str]
    status: str
    created_at: datetime


class SessionLogDisplay(SessionLogOut):
    cubesat_name: str
    instructor_name: str


class ComponentBase(BaseModel):
    name: str = Field(..., max_length=100)
    category: Literal["sensor", "board", "tool", "other"]
    image_url: Optional[str] = None

class ComponentCreate(ComponentBase):
    initial_quantity: int = Field(0, ge=0)
    tag: Optional[str] = None

class ComponentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[Literal["sensor", "board", "tool", "other"]] = None
    image_url: Optional[str] = None
    tag: Optional[str] = None

class ComponentOut(ComponentBase):
    id: int
    total_quantity: int
    created_at: datetime
    updated_at: datetime
    tag: Optional[str] = None

    class Config:
        orm_mode = True

class ComponentAdjust(BaseModel):
    delta: int  # can be positive or negative
    reason: Optional[str] = None


class ReportCreate(BaseModel):
    title: str                # short summary
    message: str              # first message / description
    cubesat_id: Optional[int] = None   # optional link to a cubesat
    image_url: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    instructor_id: int
    instructor_name: Optional[str] = None
    title: str
    status: str                # 'open', 'in_progress', 'resolved', 'closed'
    cubesat_id: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReportMessageCreate(BaseModel):
    message: str


class ReportMessageOut(BaseModel):
    id: int
    report_id: int
    sender_role: str           # 'instructor' or 'admin'
    sender_user_id: int
    message: str
    created_at: datetime


class ReportWithMessages(ReportOut):
    messages: List[ReportMessageOut]


class PackageRequestCreate(BaseModel):
    # Who will receive the package / where
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    location: Optional[str] = None       # e.g. school / city
    url_location: Optional[str] = None   # Google Maps link etc.

    # Items
    items: str                           # e.g. "4 EPS, 2 ADCS, 1 TEMP, 4 CDHS"
    total_items: int                     # e.g. 11


class PackageRequestOut(BaseModel):
    id: int
    requested_by: int
    requested_by_name: Optional[str] = None

    contact_name: Optional[str]
    contact_phone: Optional[str]
    location: Optional[str]
    url_location: Optional[str]

    items: str
    total_items: int
    status: str
    sent_date: Optional[date]
    delivered_date: Optional[date]
    coo_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PackageRequestStatusUpdate(BaseModel):
    status: Literal["on_way", "delivered", "cancelled"]
    sent_date: Optional[date] = None
    delivered_date: Optional[date] = None
    coo_comment: Optional[str] = None   
