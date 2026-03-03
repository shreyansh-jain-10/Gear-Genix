"""
ORM model definitions for the equipment booking system.

These models describe the PostgreSQL tables using SQLAlchemy ORM.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from db.database import Base


class Equipment(Base):
    """
    Equipment available for booking (e.g. projectors, microphones).
    """

    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    total_quantity = Column(Integer, nullable=False)
    available_quantity = Column(Integer, nullable=False)
    condition = Column(String, nullable=False, default="good")

    bookings = relationship("Booking", back_populates="equipment")


class Booking(Base):
    """
    Booking record describing which club has reserved which equipment and when.
    """

    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(String, unique=True, index=True)

    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    equipment = relationship("Equipment", back_populates="bookings")

    club_name = Column(String, nullable=False)
    booked_by = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(String, nullable=False, default="active")  # active/returned/cancelled
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)


class User(Base):
    """
    Registered user with a username, club affiliation, and role.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    club_name = Column(String, nullable=True)  # NULL for admin
    role = Column(String, nullable=False, default="user")  # user / admin
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.utcnow)

