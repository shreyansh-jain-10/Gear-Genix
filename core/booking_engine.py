"""
Core booking engine used by the AI agent tools.

Each function performs a specific business operation against the database
(list equipment, check availability, create bookings, etc.).  All database
access goes through SQLAlchemy ORM sessions.  Every function returns a
plain string so the agent can relay the result directly to the user.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from db.database import get_session
from db.models import Booking, Equipment


# ─── Date / time helpers ─────────────────────────────────────────────────────

_DATE_FMT = "%Y-%m-%d"
_TIME_FMT = "%H:%M"
_DATETIME_FMT = "%Y-%m-%d %H:%M"


def _parse_slot(date: str, start_time: str, end_time: str) -> tuple[datetime, datetime]:
    """
    Convert separate date and time strings into naive datetime objects.

    Raises ValueError if parsing fails — callers should handle this.
    """

    start_dt = datetime.strptime(f"{date} {start_time}", _DATETIME_FMT)
    end_dt = datetime.strptime(f"{date} {end_time}", _DATETIME_FMT)
    return start_dt, end_dt


def _fmt_time(dt: datetime) -> str:
    """Return a time string like '3:00 PM'."""
    return dt.strftime("%I:%M %p").lstrip("0")


def _fmt_date(dt: datetime) -> str:
    """Return a date string like '15 March 2025'."""
    return dt.strftime("%-d %B %Y")


# ─── Public API ───────────────────────────────────────────────────────────────


def list_equipment() -> str:
    """
    Return a formatted list of all equipment, availability, and condition.
    """

    with get_session() as session:
        try:
            stmt = select(Equipment).order_by(Equipment.name.asc())
            equipment_list: List[Equipment] = list(session.execute(stmt).scalars())
        except Exception as exc:
            return f"Failed to list equipment due to an internal error: {exc}"

    if not equipment_list:
        return "No equipment found in the system."

    lines = ["📦 Available Equipment:", "─────────────────────"]
    for i, eq in enumerate(equipment_list, start=1):
        lines.append(
            f"{i}. {eq.name} — {eq.available_quantity}/{eq.total_quantity} available ({eq.condition})"
        )
    lines.append("─────────────────────")
    return "\n".join(lines)


def check_availability(
    equipment_name: str, date: str, start_time: str, end_time: str
) -> str:
    """
    Check whether a specific piece of equipment is free for a given time slot.

    Conflict detection uses the standard interval-overlap condition:
      existing.start_time < new_end AND existing.end_time > new_start
    with status == 'active'.
    """

    try:
        start_dt, end_dt = _parse_slot(date, start_time, end_time)
    except ValueError as exc:
        return f"Invalid date or time format: {exc}"

    if end_dt <= start_dt:
        return "End time must be after start time. Please check your time slot."

    with get_session() as session:
        try:
            eq_stmt = select(Equipment).where(
                func.lower(Equipment.name) == equipment_name.lower()
            )
            equipment = session.execute(eq_stmt).scalar_one_or_none()
            if not equipment:
                return (
                    f"Equipment '{equipment_name}' not found. "
                    "Use list_equipment to see available options."
                )

            conflict_stmt = (
                select(Booking)
                .where(Booking.equipment_id == equipment.id)
                .where(Booking.status == "active")
                .where(Booking.start_time < end_dt)
                .where(Booking.end_time > start_dt)
                .order_by(Booking.start_time.asc())
            )
            conflicts: List[Booking] = list(session.execute(conflict_stmt).scalars())

            # Check available quantity separately (handles multi-unit equipment)
            if equipment.available_quantity <= 0 and not conflicts:
                return f"❌ All units of {equipment.name} are currently checked out."

            if not conflicts:
                date_label = _fmt_date(start_dt)
                return (
                    f"✅ {equipment.name} is available on {date_label} "
                    f"from {_fmt_time(start_dt)}–{_fmt_time(end_dt)}."
                )

            # Find next available slot (end of last conflict)
            last_conflict = max(conflicts, key=lambda b: b.end_time)
            conflict = conflicts[0]
            return (
                f"❌ {equipment.name} is booked from {_fmt_time(conflict.start_time)} "
                f"to {_fmt_time(conflict.end_time)} by {conflict.club_name}. "
                f"Next available after {_fmt_time(last_conflict.end_time)}."
            )
        except Exception as exc:
            return f"Failed to check availability due to an internal error: {exc}"


def _generate_booking_id(session) -> str:
    """
    Generate the next booking ID in the sequence B001, B002, ...

    Queries the current maximum booking_id and increments it instead of
    counting rows, so gaps from cancellations are handled correctly.
    """

    stmt = select(Booking.booking_id)
    all_ids = list(session.execute(stmt).scalars())

    max_num = 0
    for bid in all_ids:
        try:
            num = int(bid[1:])  # strip leading 'B'
            if num > max_num:
                max_num = num
        except (ValueError, TypeError, IndexError):
            continue

    return f"B{max_num + 1:03d}"


def make_booking(
    equipment_name: str,
    date: str,
    start_time: str,
    end_time: str,
    club_name: str,
    booked_by: str,
    telegram_username: str,
) -> str:
    """
    Create a booking for the specified equipment and time slot.

    Performs a conflict check, uses a DB transaction for all writes, and
    returns a human-readable confirmation or error message.
    """

    try:
        start_dt, end_dt = _parse_slot(date, start_time, end_time)
    except ValueError as exc:
        return f"Invalid date or time format: {exc}"

    if end_dt <= start_dt:
        return "End time must be after start time. Please check your time slot."

    with get_session() as session:
        try:
            # Resolve equipment by case-insensitive name.
            eq_stmt = select(Equipment).where(
                func.lower(Equipment.name) == equipment_name.lower()
            )
            equipment = session.execute(eq_stmt).scalar_one_or_none()
            if not equipment:
                return (
                    f"Equipment '{equipment_name}' not found. "
                    "Use list_equipment to see available options."
                )

            if equipment.available_quantity <= 0:
                return f"❌ All units of {equipment.name} are currently checked out."

            # Overlap conflict check.
            conflict_stmt = (
                select(Booking)
                .where(Booking.equipment_id == equipment.id)
                .where(Booking.status == "active")
                .where(Booking.start_time < end_dt)
                .where(Booking.end_time > start_dt)
            )
            conflict = session.execute(conflict_stmt).scalar_one_or_none()
            if conflict:
                return (
                    f"❌ {equipment.name} is already booked from "
                    f"{_fmt_time(conflict.start_time)} to {_fmt_time(conflict.end_time)} "
                    f"by {conflict.club_name}. Please choose a different time slot."
                )

            booking_id = _generate_booking_id(session)

            booking = Booking(
                booking_id=booking_id,
                equipment_id=equipment.id,
                club_name=club_name,
                booked_by=booked_by,
                telegram_username=telegram_username,
                start_time=start_dt,
                end_time=end_dt,
                status="active",
            )
            session.add(booking)
            equipment.available_quantity -= 1
            session.commit()

            eq_name = equipment.name  # capture before session closes

        except Exception as exc:
            session.rollback()
            return f"Failed to create booking due to an internal error: {exc}"

    date_label = _fmt_date(start_dt)
    return (
        f"✅ Booking Confirmed!\n"
        f"─────────────────────\n"
        f"Equipment : {eq_name}\n"
        f"Club      : {club_name}\n"
        f"Date      : {date_label}\n"
        f"Time      : {_fmt_time(start_dt)} – {_fmt_time(end_dt)}\n"
        f"Booking ID: {booking_id}\n"
        f"Contact   : {booked_by} ({telegram_username})\n"
        f"─────────────────────\n"
        f"Save your Booking ID — you will need it to cancel or return."
    )


def get_bookings(club_name: str) -> str:
    """
    Fetch all active bookings for a given club and return a formatted list.

    Uses a case-insensitive partial match on club_name.
    """

    with get_session() as session:
        try:
            stmt = (
                select(Booking)
                .options(selectinload(Booking.equipment))
                .join(Equipment)
                .where(Booking.club_name.ilike(f"%{club_name}%"))
                .where(Booking.status == "active")
                .order_by(Booking.start_time.asc())
            )
            bookings: List[Booking] = list(session.execute(stmt).scalars())

            if not bookings:
                return f"No active bookings found for {club_name}."

            lines = [f"📋 Active Bookings for {club_name}:", "─────────────────────"]
            for b in bookings:
                date_label = b.start_time.strftime("%-d %b")
                lines.append(
                    f"{b.booking_id} | {b.equipment.name} | {date_label} | "
                    f"{_fmt_time(b.start_time)}–{_fmt_time(b.end_time)}"
                )
            lines.append("─────────────────────")
            return "\n".join(lines)

        except Exception as exc:
            return f"Failed to fetch bookings due to an internal error: {exc}"


def cancel_booking(booking_id: str) -> str:
    """
    Cancel an active booking and release one unit of the associated equipment.
    """

    with get_session() as session:
        try:
            stmt = select(Booking).where(
                func.upper(Booking.booking_id) == booking_id.upper()
            )
            booking = session.execute(stmt).scalar_one_or_none()
            if not booking:
                return f"Booking {booking_id} not found."

            if booking.status != "active":
                return (
                    f"Booking {booking_id} is already {booking.status} "
                    f"and cannot be cancelled."
                )

            eq_stmt = select(Equipment).where(Equipment.id == booking.equipment_id)
            equipment = session.execute(eq_stmt).scalar_one_or_none()

            booking.status = "cancelled"
            if equipment:
                equipment.available_quantity += 1
            session.commit()

            eq_name = equipment.name if equipment else "the equipment"

        except Exception as exc:
            session.rollback()
            return f"Failed to cancel booking due to an internal error: {exc}"

    return (
        f"✅ Booking {booking_id} has been cancelled. "
        f"{eq_name} is now available."
    )


def return_equipment(booking_id: str) -> str:
    """
    Mark equipment as returned for an active booking and increment availability.
    """

    with get_session() as session:
        try:
            stmt = select(Booking).where(
                func.upper(Booking.booking_id) == booking_id.upper()
            )
            booking = session.execute(stmt).scalar_one_or_none()
            if not booking:
                return f"Booking {booking_id} not found."

            if booking.status != "active":
                return f"Booking {booking_id} is already {booking.status}."

            eq_stmt = select(Equipment).where(Equipment.id == booking.equipment_id)
            equipment = session.execute(eq_stmt).scalar_one_or_none()

            booking.status = "returned"
            if equipment:
                equipment.available_quantity += 1
            session.commit()

            eq_name = equipment.name if equipment else "the equipment"

        except Exception as exc:
            session.rollback()
            return f"Failed to mark equipment as returned due to an internal error: {exc}"

    return (
        f"✅ Equipment returned successfully. "
        f"Booking {booking_id} marked as returned. "
        f"{eq_name} is back in the pool."
    )


def get_active_bookings() -> str:
    """
    Retrieve all currently active bookings across all clubs.
    """

    with get_session() as session:
        try:
            stmt = (
                select(Booking)
                .options(selectinload(Booking.equipment))
                .join(Equipment)
                .where(Booking.status == "active")
                .order_by(Booking.start_time.asc())
            )
            bookings: List[Booking] = list(session.execute(stmt).scalars())

            if not bookings:
                return "No active bookings at the moment."

            lines = ["📋 All Active Bookings:", "─────────────────────"]
            for b in bookings:
                date_label = b.start_time.strftime("%-d %b")
                lines.append(
                    f"{b.booking_id} | {b.equipment.name} | {b.club_name} | "
                    f"{b.booked_by} | {date_label} {_fmt_time(b.start_time)}–{_fmt_time(b.end_time)}"
                )
            lines.append("─────────────────────")
            return "\n".join(lines)

        except Exception as exc:
            return f"Failed to fetch active bookings due to an internal error: {exc}"
