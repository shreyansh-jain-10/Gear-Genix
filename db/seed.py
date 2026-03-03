"""
Seed script to populate initial equipment data.

This module can be invoked at application startup to ensure that the
equipment table always contains the baseline set of items used by clubs.
"""

from __future__ import annotations

from typing import List, Dict

from sqlalchemy import func, select

from db.database import Base, engine, get_session
import config
from db.models import Booking, Equipment, User


SEED_EQUIPMENT: List[Dict[str, object]] = [
    {"name": "Projector", "total_quantity": 2, "condition": "good"},
    {"name": "Microphone", "total_quantity": 3, "condition": "good"},
    {"name": "Bluetooth Speaker", "total_quantity": 2, "condition": "good"},
    {"name": "Laptop", "total_quantity": 2, "condition": "good"},
    {"name": "HDMI Cable", "total_quantity": 5, "condition": "good"},
    {"name": "Extension Cord", "total_quantity": 4, "condition": "good"},
    {"name": "DSLR Camera", "total_quantity": 1, "condition": "good"},
    {"name": "Tripod", "total_quantity": 2, "condition": "good"},
]


def init_db() -> None:
    """
    Create all database tables based on ORM models.

    For production systems, Alembic migrations should be preferred, but this
    helper ensures a working schema for local development and testing.
    """

    Base.metadata.create_all(bind=engine)


def seed_equipment() -> None:
    """
    Insert baseline equipment rows if they do not already exist.

    The function is idempotent: running it multiple times will not create
    duplicate equipment entries.
    """

    with get_session() as session:
        try:
            for item in SEED_EQUIPMENT:
                stmt = select(Equipment).where(Equipment.name == item["name"])
                existing = session.execute(stmt).scalar_one_or_none()
                if existing:
                    continue

                equipment = Equipment(
                    name=item["name"],
                    total_quantity=item["total_quantity"],
                    available_quantity=item["total_quantity"],
                    condition=item["condition"],
                )
                session.add(equipment)

            # If there are no active bookings, reset availability to total
            # so stale counts from dropped/cleared bookings don't persist.
            active_count = session.execute(
                select(func.count()).select_from(Booking).where(Booking.status == "active")
            ).scalar()
            if active_count == 0:
                all_equipment = list(session.execute(select(Equipment)).scalars())
                for eq in all_equipment:
                    eq.available_quantity = eq.total_quantity

            session.commit()
        except Exception:
            session.rollback()
            raise


def seed_admin_user() -> None:
    """
    Ensure the admin user from ADMIN_USERNAME env var exists.

    Idempotent: updates role to admin if the username exists but isn't admin.
    """

    with get_session() as session:
        try:
            stmt = select(User).where(User.username == config.ADMIN_USERNAME)
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                if existing.role != "admin":
                    existing.role = "admin"
                    existing.club_name = None
                    session.commit()
                return

            admin = User(
                username=config.ADMIN_USERNAME,
                club_name=None,
                role="admin",
            )
            session.add(admin)
            session.commit()
        except Exception:
            session.rollback()
            raise

