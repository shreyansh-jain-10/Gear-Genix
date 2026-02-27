"""
Tool execution layer that bridges OpenAI function calls to the booking engine.

ToolExecutor maps tool names (as strings) to the corresponding Python
functions in core/booking_engine.py.  Every call is wrapped in try/except
so unexpected errors surface as readable strings rather than exceptions.
"""

from __future__ import annotations

from typing import Any, Dict

from core import booking_engine


class ToolExecutor:
    """
    Dispatches tool calls from the agent loop to booking_engine functions.
    """

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute the named tool with the given arguments and return a string result.

        Returns a clear error string on failure — never raises an exception.
        """

        try:
            if tool_name == "list_equipment":
                return booking_engine.list_equipment()

            if tool_name == "check_availability":
                return booking_engine.check_availability(
                    equipment_name=str(arguments.get("equipment_name", "")),
                    date=str(arguments.get("date", "")),
                    start_time=str(arguments.get("start_time", "")),
                    end_time=str(arguments.get("end_time", "")),
                )

            if tool_name == "make_booking":
                return booking_engine.make_booking(
                    equipment_name=str(arguments.get("equipment_name", "")),
                    date=str(arguments.get("date", "")),
                    start_time=str(arguments.get("start_time", "")),
                    end_time=str(arguments.get("end_time", "")),
                    club_name=str(arguments.get("club_name", "")),
                    booked_by=str(arguments.get("booked_by", "")),
                    telegram_username=str(arguments.get("telegram_username", "")),
                )

            if tool_name == "get_bookings":
                return booking_engine.get_bookings(
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

            return f"Unknown tool '{tool_name}'. No action was taken."

        except Exception as exc:
            return f"Tool '{tool_name}' encountered an unexpected error: {exc}"
