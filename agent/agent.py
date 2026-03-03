"""
Core AI agent implementation using OpenAI GPT-5.2 with function calling.

EquipmentBookingAgent follows the ReAct pattern: it calls tools, observes
their results, and produces a final natural-language response.  Today's date
is injected dynamically into the system prompt on every turn so the model
can resolve relative dates correctly.

Sessions require username-based login before the normal chat loop begins.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from openai import OpenAI

import config
from agent.memory import ConversationMemory, memory as global_memory
from agent.prompts import SYSTEM_PROMPT
from agent.tool_executor import ToolExecutor
from agent.tools import TOOLS
from core.booking_engine import lookup_user


logger = logging.getLogger(__name__)


class EquipmentBookingAgent:
    """
    Orchestrates the OpenAI API, conversation memory, and tool execution.
    """

    def __init__(self) -> None:
        """Initialise the OpenAI client, memory store, and tool executor."""

        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.memory: ConversationMemory = global_memory
        self.tool_executor = ToolExecutor()
        self.model = "gpt-5.2"
        self.max_tool_iterations = 10

    def _build_system_message(self, session_id: str) -> Dict[str, Any]:
        """
        Build the system message with today's date and user context injected.
        """

        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%I:%M %p").lstrip("0")

        user_ctx = self.memory.get_user_context(session_id)
        user_info_block = ""
        if user_ctx:
            if user_ctx["role"] == "admin":
                user_info_block = (
                    f"\n\nLOGGED-IN USER: {user_ctx['username']} (ADMIN)"
                    "\nThis user is an admin with full access to all operations."
                    "\nThey can add users, remove users, and manage all bookings."
                    "\nWhen admin wants to book, they must specify the club name."
                )
            else:
                club = user_ctx["club_name"]
                user_info_block = (
                    f"\n\nLOGGED-IN USER: {user_ctx['username']} (Club: {club})"
                    f"\nThis user can ONLY make/cancel/return bookings for {club}."
                    f"\nAutomatically use '{club}' as the club name for their bookings — do NOT ask."
                    f"\nThey can view all active bookings but can only view history for {club}."
                )

        return {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + f"\n\nCurrent date: {date_str}"
                + f"\nCurrent time: {time_str}"
                + user_info_block
                + "\n\nIMPORTANT: Always call the appropriate tool (list_equipment, "
                  "get_bookings, get_active_bookings, check_availability) when the user "
                  "asks about equipment, bookings, or availability — NEVER answer from "
                  "conversation history as data changes with every booking, cancellation, "
                  "and return."
            ),
        }

    # ── Login flow ─────────────────────────────────────────────────────────

    def _handle_login(self, session_id: str, user_message: str) -> str:
        """Handle the login flow before normal chat begins."""

        history = self.memory.get_history(session_id)

        # First message in this session — greet and ask for username
        if len(history) == 0:
            greeting = (
                "👋 Welcome to Gear Genix!\n"
                "I need to verify your identity first.\n"
                "Please enter your username:"
            )
            self.memory.add_message(session_id, "user", user_message)
            self.memory.add_message(session_id, "assistant", greeting)
            return greeting

        # Subsequent messages — treat as username attempt
        username = user_message.strip()
        user_info = lookup_user(username)

        if user_info is None:
            error_msg = (
                f"Username '{username}' not found.\n"
                "Please check your username or contact the admin to get registered."
            )
            self.memory.add_message(session_id, "user", user_message)
            self.memory.add_message(session_id, "assistant", error_msg)
            return error_msg

        # Valid user — bind to session and clear login conversation
        self.memory.set_user_context(
            session_id,
            username=user_info["username"],
            club_name=user_info["club_name"],
            role=user_info["role"],
        )
        self.memory.clear_messages(session_id)

        if user_info["role"] == "admin":
            welcome = (
                f"Welcome, {user_info['username']}! You are logged in as admin.\n"
                "You have full access to all operations including managing users.\n"
                "How can I help you today?"
            )
        else:
            welcome = (
                f"Welcome, {user_info['username']}! "
                f"You are a member of {user_info['club_name']}.\n"
                "How can I help you today?"
            )

        self.memory.add_message(session_id, "assistant", welcome)
        return welcome

    # ── Main chat loop ─────────────────────────────────────────────────────

    def chat(self, session_id: str, user_message: str) -> str:
        """
        Process a user message and return the agent's natural-language reply.

        Implements login gate + full ReAct loop:
        1. If not logged in, handle login flow.
        2. Add user message to memory.
        3. Build message list (fresh system prompt + history).
        4. Call OpenAI API.
        5. If finish_reason == 'tool_calls': execute tools, add results, repeat.
        6. If finish_reason == 'stop': return the assistant's text.
        """

        if not user_message:
            return "Please send a message so I can help you."

        # Login gate
        if not self.memory.is_logged_in(session_id):
            return self._handle_login(session_id, user_message)

        self.memory.add_message(session_id, "user", user_message)

        user_ctx = self.memory.get_user_context(session_id)

        for iteration in range(self.max_tool_iterations):
            messages: List[Dict[str, Any]] = [
                self._build_system_message(session_id)
            ] + self.memory.get_history(session_id)

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
            except Exception as exc:
                logger.exception("OpenAI API call failed")
                error_msg = (
                    "I'm having trouble right now. Please try again in a moment."
                )
                self.memory.add_message(session_id, "assistant", error_msg)
                return error_msg

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            message = choice.message

            # ── Final response ─────────────────────────────────────────────
            if finish_reason == "stop":
                reply = message.content or "I wasn't able to generate a response. Please try again."
                self.memory.add_message(session_id, "assistant", reply)
                return reply

            # ── Tool calls ─────────────────────────────────────────────────
            if finish_reason == "tool_calls" and message.tool_calls:
                # Record the assistant message with its tool_calls.
                tool_calls_payload = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
                self.memory.add_assistant_tool_call(session_id, tool_calls_payload)

                # Execute each tool and record the results.
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        arguments = {}

                    logger.info("Executing tool: %s with args: %s", tool_name, arguments)
                    result = self.tool_executor.execute(tool_name, arguments, user_context=user_ctx)
                    logger.info("Tool result: %s", result[:200])

                    self.memory.add_tool_result(session_id, tool_call.id, result)

                # Loop back to call the API again with updated history.
                continue

            # ── Unexpected finish reason ───────────────────────────────────
            logger.warning("Unexpected finish_reason: %s", finish_reason)
            fallback = (
                "I received an unexpected response. Please try rephrasing your message."
            )
            self.memory.add_message(session_id, "assistant", fallback)
            return fallback

        # Exceeded max iterations.
        timeout_msg = (
            "I encountered an issue processing your request. Please try again."
        )
        self.memory.add_message(session_id, "assistant", timeout_msg)
        return timeout_msg


# Shared singleton used by the API and Telegram bot.
agent = EquipmentBookingAgent()
