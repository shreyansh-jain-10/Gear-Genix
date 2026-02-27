"""
Core AI agent implementation using OpenAI GPT-4o-mini with function calling.

EquipmentBookingAgent follows the ReAct pattern: it calls tools, observes
their results, and produces a final natural-language response.  Today's date
is injected dynamically into the system prompt on every turn so the model
can resolve relative dates correctly.
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
        self.model = "gpt-4o"
        self.max_tool_iterations = 10

    def _build_system_message(self) -> Dict[str, Any]:
        """
        Build the system message with today's date injected dynamically.

        The date is appended on every call so the model always knows the
        current date when resolving relative expressions like 'tomorrow'.
        """

        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%I:%M %p").lstrip("0")
        return {
            "role": "system",
            "content": (
                SYSTEM_PROMPT
                + f"\n\nCurrent date: {date_str}"
                + f"\nCurrent time: {time_str}"
                + "\n\nIMPORTANT: Always call list_equipment when asked about available "
                  "equipment or inventory — never answer from conversation history as "
                  "availability changes with every booking and return."
            ),
        }

    def chat(self, session_id: str, user_message: str) -> str:
        """
        Process a user message and return the agent's natural-language reply.

        Implements the full ReAct loop:
        1. Add user message to memory.
        2. Build message list (fresh system prompt + history).
        3. Call OpenAI API.
        4. If finish_reason == 'tool_calls': execute tools, add results, repeat.
        5. If finish_reason == 'stop': return the assistant's text.
        """

        if not user_message:
            return "Please send a message so I can help you."

        self.memory.add_message(session_id, "user", user_message)

        for iteration in range(self.max_tool_iterations):
            messages: List[Dict[str, Any]] = [
                self._build_system_message()
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
                    "⚠️ I'm having trouble connecting to my AI backend right now. "
                    "Please try again in a moment."
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
                    result = self.tool_executor.execute(tool_name, arguments)
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
