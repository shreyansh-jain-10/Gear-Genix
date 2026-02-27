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
                "Requires all 7 parameters. Always call check_availability first."
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
                    "telegram_username": {
                        "type": "string",
                        "description": "Telegram username (with or without @) of the contact person.",
                    },
                },
                "required": [
                    "equipment_name",
                    "date",
                    "start_time",
                    "end_time",
                    "club_name",
                    "booked_by",
                    "telegram_username",
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
            "name": "cancel_booking",
            "description": "Cancel an active booking using its Booking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {
                        "type": "string",
                        "description": "Booking ID in the format B001, B002, etc.",
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
                        "description": "Booking ID in the format B001, B002, etc.",
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
]
