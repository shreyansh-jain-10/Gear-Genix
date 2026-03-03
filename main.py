"""
Main entry point for EquiBot.

Startup sequence:
1. Validate config (triggers EnvironmentError if keys are missing)
2. Create all DB tables and seed equipment data
3. Start FastAPI (uvicorn) in a background thread on port 8000
4. Start Telegram bot (polling) in the main thread
   — if TELEGRAM_BOT_TOKEN is absent, only the web server runs
"""

from __future__ import annotations

import logging
import threading

import uvicorn

from db.seed import init_db, seed_equipment, seed_admin_user


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_api() -> None:
    """
    Start the FastAPI application using Uvicorn in a background thread.
    """

    from api.main import app  # imported here to avoid circular imports at module level
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


def main() -> None:
    """
    Initialise infrastructure and start all services.
    """

    print("🚀 EquiBot starting up...")

    # ── Step 1: validate config ──────────────────────────────────────────
    try:
        import config  # noqa: F401 — triggers validation on import
    except EnvironmentError as exc:
        print(f"❌ Configuration error: {exc}")
        return

    # ── Step 2: database ─────────────────────────────────────────────────
    try:
        init_db()
        print("📦 Database initialised")
        seed_equipment()
        print("🌱 Seed data loaded")
        seed_admin_user()
        print("🔐 Admin user seeded")
    except Exception as exc:
        print(f"❌ Database error: {exc}")
        print("   Check that PostgreSQL is running and DATABASE_URL is correct.")
        return

    # ── Step 3: FastAPI in background thread ─────────────────────────────
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    print("🌐 Web UI running at http://localhost:8000/ui/index.html")
    print("📡 API running at http://localhost:8000")

    # ── Step 4: Telegram bot ─────────────────────────────────────────────
    import config as cfg

    if not cfg.TELEGRAM_BOT_TOKEN:
        print("⚠️  TELEGRAM_BOT_TOKEN not set — Telegram bot will not start.")
        print("✅ EquiBot is ready! (Web UI only)")
        # Keep main thread alive so the daemon API thread keeps running.
        api_thread.join()
        return

    print("🤖 Telegram bot starting...")
    print("✅ EquiBot is ready!")

    try:
        from bot.telegram_bot import build_telegram_app
        telegram_app = build_telegram_app()
        telegram_app.run_polling()
    except Exception as exc:
        print(f"❌ Telegram bot error: {exc}")
        print("   The web UI is still running at http://localhost:8000")
        api_thread.join()


if __name__ == "__main__":
    main()
