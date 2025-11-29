# backend/schemas.py
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
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
    m3_10mm: int = 0
    m3_10mm_thread: int = 0
    m3_9mm_thread: int = 0
    m3_20mm_thread: int = 0
    m3_6mm: int = 0


class CubesatOut(BaseModel):
    id: int
    name: str
    status: str
    location: Optional[str]
    delivered_date: Optional[date]
    instructor_id: Optional[int]

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
    m3_10mm: int
    m3_10mm_thread: int
    m3_9mm_thread: int
    m3_20mm_thread: int
    m3_6mm: int

    is_complete: bool
    missing_items: Optional[str]
    is_received: bool = False
    received_date: Optional[date] = None


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str


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
    instructor_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    max_participants: Optional[int] = None
    current_participants: int = 0
    requirements: Optional[str] = None
    notes: Optional[str] = None


class WorkshopCreate(WorkshopBase):
    pass


class WorkshopOut(WorkshopBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True