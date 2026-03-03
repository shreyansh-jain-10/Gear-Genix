"""
OpenAI function-calling tool schema definitions.

TOOLS is a list of tool specs passed directly to the OpenAI Chat API.
Each entry follows the standard OpenAI function-calling schema format.
"""

from __future__ import annotations

from typing import Any, Dict, List


TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_equipment",
            "description": (
                "List all equipment with name, total quantity, "
                "available quantity, and condition."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check if a specific equipment is available for a given date and time slot. "
                "Always call this before make_booking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment_name": {
                        "type": "string",
                        "description": "Name of the equipment to check (case-insensitive).",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the booking in YYYY-MM-DD format.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM 24-hour format.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in HH:MM 24-hour format.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to check availability for. Defaults to 1 if not specified.",
                    },
                },
                "required": ["equipment_name", "date", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "make_booking",
            "description": (
                "Create a new equipment booking after confirming availability. "
                "Always call check_availability first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment_name": {
                        "type": "string",
                        "description": "Name of the equipment to book (case-insensitive).",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the booking in YYYY-MM-DD format.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM 24-hour format.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in HH:MM 24-hour format.",
                    },
                    "club_name": {
                        "type": "string",
                        "description": "Name of the club making the booking.",
                    },
                    "booked_by": {
                        "type": "string",
                        "description": "Full name of the person responsible for the booking.",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of units to book. Defaults to 1 if not specified.",
                    },
                },
                "required": [
                    "equipment_name",
                    "date",
                    "start_time",
                    "end_time",
                    "club_name",
                    "booked_by",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bookings",
            "description": "Get all active bookings for a specific club.",
            "parameters": {
                "type": "object",
                "properties": {
                    "club_name": {
                        "type": "string",
                        "description": "Name of the club whose bookings should be listed.",
                    },
                },
                "required": ["club_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_history",
            "description": "Get past bookings (returned or cancelled) for a specific club. Use this when the user asks for booking history or past bookings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "club_name": {
                        "type": "string",
                        "description": "Name of the club whose past bookings should be listed.",
                    },
                },
                "required": ["club_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an active booking using its Booking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "The EXACT Booking ID as provided by the user (e.g. B006). Do NOT modify, reformat, or guess — pass it exactly as the user typed it.",
                    },
                },
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "return_equipment",
            "description": "Mark equipment as returned using Booking ID. Updates availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "The EXACT Booking ID as provided by the user (e.g. B006). Do NOT modify, reformat, or guess — pass it exactly as the user typed it.",
                    },
                },
                "required": ["booking_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_bookings",
            "description": (
                "Get all currently active bookings across all clubs. "
                "Use for admin queries like 'who has the projector'."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_booking_history",
            "description": (
                "Get past bookings (returned or cancelled) across all clubs. "
                "Admin only. Use when user asks for booking history of all clubs."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_user",
            "description": (
                "Add a new user to the system with a username and club assignment. "
                "Admin only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The username for the new user.",
                    },
                    "club_name": {
                        "type": "string",
                        "description": "The club to assign the user to.",
                    },
                },
                "required": ["username", "club_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": (
                "List all users in the system with their club and role. Admin only."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_user",
            "description": (
                "Remove an existing user from the system. Admin only. "
                "Cannot remove admin users."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "The username to remove.",
                    },
                },
                "required": ["username"],
            },
        },
    },
]
