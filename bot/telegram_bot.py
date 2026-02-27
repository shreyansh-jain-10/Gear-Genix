"""
Telegram bot interface using python-telegram-bot (async).

Connects incoming Telegram messages to the EquipmentBookingAgent and
maintains per-chat conversation memory using the chat_id as session_id.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from agent.agent import agent
from agent.memory import memory
import config


logger = logging.getLogger(__name__)


WELCOME_TEXT = (
    "👋 Welcome to Gear Genix — College Equipment Booking Assistant!\n\n"
    "I can help you:\n"
    "• 📦 Check what equipment is available\n"
    "• 🔍 Check availability for a time slot\n"
    "• 📅 Book equipment for your club\n"
    "• 📋 View your club's bookings\n"
    "• ❌ Cancel a booking\n"
    "• 🔄 Return equipment\n\n"
    "Just tell me what you need in plain English!\n"
    "Example: 'Is the projector free tomorrow 3-5pm?'"
)

HELP_TEXT = (
    "Here are some things you can ask me:\n\n"
    "📦 'What equipment do you have?'\n"
    "🔍 'Is the projector free on Friday 2-4pm?'\n"
    "📅 'Book a mic for Robotics Club tomorrow 10am-12pm'\n"
    "📋 'Show bookings for Drama Club'\n"
    "❌ 'Cancel booking B007'\n"
    "🔄 'Return equipment for booking B005'\n"
    "👁 'Who has the projector right now?'"
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — send the welcome message."""

    if update.effective_chat:
        await update.effective_chat.send_message(WELCOME_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — show example queries."""

    if update.effective_chat:
        await update.effective_chat.send_message(HELP_TEXT)


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear — reset conversation history for this chat."""

    if update.effective_chat:
        session_id = str(update.effective_chat.id)
        memory.clear_history(session_id)
        await update.effective_chat.send_message(
            "🗑️ Conversation cleared! Starting fresh."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any non-command text message by passing it to the agent."""

    if not update.effective_chat or not update.message:
        return

    session_id = str(update.effective_chat.id)
    text = (update.message.text or "").strip()
    if not text:
        return

    try:
        # Show typing indicator while the agent is working.
        await update.effective_chat.send_chat_action(ChatAction.TYPING)

        # Run the synchronous agent in a thread pool to avoid blocking the event loop.
        loop = asyncio.get_running_loop()
        reply = await loop.run_in_executor(None, agent.chat, session_id, text)
    except Exception:
        logger.exception("Agent failed to handle Telegram message")
        reply = "⚠️ Something went wrong. Please try again."

    await update.message.reply_text(reply)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler — log unexpected exceptions from the bot framework."""

    logger.exception("Unhandled exception in Telegram bot: %s", context.error)


def build_telegram_app() -> Application:
    """
    Build and return the configured Telegram Application.

    Returns the Application object; callers invoke app.run_polling() to start.
    """

    application = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    return application
