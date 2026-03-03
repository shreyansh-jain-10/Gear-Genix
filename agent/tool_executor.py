"""
Tool execution layer that bridges OpenAI function calls to the booking engine.

ToolExecutor maps tool names (as strings) to the corresponding Python
functions in core/booking_engine.py.  Every call is wrapped in try/except
so unexpected errors surface as readable strings rather than exceptions.

Permission enforcement happens here — this is the security boundary.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select

from core import booking_engine
from db.database import get_session
from db.models import Booking


class ToolExecutor:
    """
    Dispatches tool calls from the agent loop to booking_engine functions.
    Enforces permissions based on user context before executing any tool.
    """

    def _verify_booking_ownership(self, booking_id: str, user_club: str) -> Optional[str]:
        """
        Check if a booking belongs to the user's club.
        Returns an error message if not, None if ownership is confirmed.
        """

        with get_session() as session:
            stmt = select(Booking).where(Booking.booking_id == booking_id.strip())
            booking = session.execute(stmt).scalar_one_or_none()
            if not booking:
                return None  # Let the actual tool handle "not found"
            if booking.club_name.lower().strip() != user_club.lower().strip():
                return (
                    f"You can only manage bookings for your club ({user_club}). "
                    f"Booking {booking_id} belongs to {booking.club_name}."
                )
        return None

    def _check_permission(
        self, tool_name: str, arguments: Dict[str, Any], user_context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Return an error message if the user is NOT allowed to perform this action.
        Return None if the action is permitted.
        """

        if user_context is None:
            return "You must be logged in to perform this action."

        role = user_context.get("role", "user")
        user_club = user_context.get("club_name")

        # Admin can do everything
        if role == "admin":
            return None

        # ── Regular user restrictions ──────────────────────────────────────

        # User management is admin-only
        if tool_name in ("add_user", "remove_user", "list_users"):
            return "Only admins can manage users. Please contact your admin."

        # All-clubs booking history is admin-only
        if tool_name == "get_all_booking_history":
            return (
                f"You can only view booking history for your club ({user_club})."
            )

        # Booking: force own club
        if tool_name == "make_booking":
            requested_club = arguments.get("club_name", "")
            if requested_club.lower().strip() != user_club.lower().strip():
                # Silently override to user's club instead of rejecting
                arguments["club_name"] = user_club

        # Club-specific views: enforce own club
        if tool_name == "get_bookings":
            requested_club = arguments.get("club_name", "")
            if requested_club.lower().strip() != user_club.lower().strip():
                return f"You can only view bookings for your club ({user_club})."

        if tool_name == "get_booking_history":
            requested_club = arguments.get("club_name", "")
            if requested_club.lower().strip() != user_club.lower().strip():
                return f"You can only view booking history for your club ({user_club})."

        # Cancel / return: verify booking belongs to user's club
        if tool_name in ("cancel_booking", "return_equipment"):
            booking_id = arguments.get("booking_id", "")
            ownership_error = self._verify_booking_ownership(booking_id, user_club)
            if ownership_error:
                return ownership_error

        # These are allowed for all users:
        # list_equipment, check_availability, get_active_bookings
        return None

    def execute(
        self, tool_name: str, arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute the named tool with the given arguments and return a string result.

        Permission check runs first — if denied, the tool is never called.
        Returns a clear error string on failure — never raises an exception.
        """

        try:
            # Permission check FIRST
            permission_error = self._check_permission(tool_name, arguments, user_context)
            if permission_error:
                return permission_error

            if tool_name == "list_equipment":
                return booking_engine.list_equipment()

            if tool_name == "check_availability":
                return booking_engine.check_availability(
                    equipment_name=str(arguments.get("equipment_name", "")),
                    date=str(arguments.get("date", "")),
                    start_time=str(arguments.get("start_time", "")),
                    end_time=str(arguments.get("end_time", "")),
                    quantity=int(arguments.get("quantity", 1)),
                )

            if tool_name == "make_booking":
                return booking_engine.make_booking(
                    equipment_name=str(arguments.get("equipment_name", "")),
                    date=str(arguments.get("date", "")),
                    start_time=str(arguments.get("start_time", "")),
                    end_time=str(arguments.get("end_time", "")),
                    club_name=str(arguments.get("club_name", "")),
                    booked_by=str(arguments.get("booked_by", "")),
                    quantity=int(arguments.get("quantity", 1)),
                )

            if tool_name == "get_bookings":
                return booking_engine.get_bookings(
                    club_name=str(arguments.get("club_name", "")),
                )

            if tool_name == "get_booking_history":
                return booking_engine.get_booking_history(
                    club_name=str(arguments.get("club_name", "")),
                )

            if tool_name == "cancel_booking":
                return booking_engine.cancel_booking(
                    booking_id=str(arguments.get("booking_id", "")),
                )

            if tool_name == "return_equipment":
                return booking_engine.return_equipment(
                    booking_id=str(arguments.get("booking_id", "")),
                )

            if tool_name == "get_active_bookings":
                return booking_engine.get_active_bookings()

            if tool_name == "get_all_booking_history":
                return booking_engine.get_all_booking_history()

            if tool_name == "list_users":
                return booking_engine.list_users()

            if tool_name == "add_user":
                return booking_engine.add_user(
                    username=str(arguments.get("username", "")),
                    club_name=str(arguments.get("club_name", "")),
                )

            if tool_name == "remove_user":
                return booking_engine.remove_user(
                    username=str(arguments.get("username", "")),
                )

            return f"Unknown tool '{tool_name}'. No action was taken."

        except Exception as exc:
            return f"Tool '{tool_name}' encountered an unexpected error: {exc}"
