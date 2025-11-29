# backend/models.py
from sqlalchemy import Column, Integer, String, Date, Enum, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    admin = "admin"
    operations = "operations"
    instructor = "instructor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False)


class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", backref="instructor_profile")

    cubesats = relationship("Cubesat", back_populates="instructor")


class CubesatStatus(str, enum.Enum):
    working = "working"
    damaged = "damaged"
    repeating = "repeating"


class Cubesat(Base):
    __tablename__ = "cubesats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    status = Column(Enum(CubesatStatus), nullable=False, default=CubesatStatus.working)
    location = Column(String(100), nullable=True)
    delivered_date = Column(Date, nullable=True)

    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=True)
    instructor = relationship("Instructor", back_populates="cubesats")

    # Checklist stored as counts
    structures = Column(Integer, default=0)
    current_sensors = Column(Integer, default=0)
    temp_sensors = Column(Integer, default=0)
    fram = Column(Integer, default=0)
    sd_card = Column(Integer, default=0)
    reaction_wheel = Column(Integer, default=0)
    mpu = Column(Integer, default=0)
    gps = Column(Integer, default=0)
    motor_driver = Column(Integer, default=0)
    phillips_screwdriver = Column(Integer, default=0)
    screw_gauge_3d = Column(Integer, default=0)
    standoff_tool_3d = Column(Integer, default=0)
    m3_10mm = Column(Integer, default=0)
    m3_10mm_thread = Column(Integer, default=0)
    m3_9mm_thread = Column(Integer, default=0)
    m3_20mm_thread = Column(Integer, default=0)
    m3_6mm = Column(Integer, default=0)

    is_complete = Column(Boolean, default=False)
    missing_items = Column(Text, nullable=True)


class ReceiptStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"


class Receipt(Base):
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    cubesat_id = Column(Integer, ForeignKey("cubesats.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=False)
    items = Column(Text, nullable=False)  # JSON string of items
    status = Column(Enum(ReceiptStatus), default=ReceiptStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)


class NotificationType(str, enum.Enum):
    info = "info"
    warning = "warning"
    alert = "alert"
    receipt_approval = "receipt_approval"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(Enum(NotificationType), default=NotificationType.info)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # For linking to entities like receipts
    related_entity_id = Column(Integer, nullable=True)
    related_entity_type = Column(String(50), nullable=True)  # e.g., "receipt"
