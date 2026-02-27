# EquiBot — College Equipment Booking Bot

An AI agent that lets college clubs and departments book shared equipment
(projectors, microphones, speakers, laptops, etc.) through natural conversation.

Accessible via **Telegram** and a **lightweight web UI**.

---

## Setup

### 1. Clone the repo
```bash
git clone <repo-url>
cd equipment-booking-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create the PostgreSQL database
```bash
createdb equipment_booking
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 5. Run
```bash
python main.py
```

---

## Getting API Keys

**OpenAI**
- Visit https://platform.openai.com
- Create an API key under *API Keys*

**Telegram Bot Token**
- Open Telegram and message **@BotFather**
- Run `/newbot` and follow the prompts
- Copy the token provided

---

## Usage

**Web UI**
Open http://localhost:8000/ui/index.html in your browser.

**Telegram**
Search for your bot's username and start a conversation.

---

## Example Commands

| What you type | What happens |
|---|---|
| `What equipment do you have?` | Lists all equipment with availability |
| `Is the projector free tomorrow 3-5pm?` | Checks availability |
| `Book a mic for Robotics Club on Friday 10am-12pm` | Starts booking flow |
| `Show bookings for Robotics Club` | Lists active bookings |
| `Cancel booking B007` | Cancels a booking |
| `Return equipment for booking B005` | Marks equipment as returned |
| `Who has the projector right now?` | Admin view of all active bookings |

---

## Project Structure

```
equipment-booking-bot/
├── agent/
│   ├── agent.py          # Core ReAct agent loop
│   ├── tools.py          # OpenAI function schemas
│   ├── tool_executor.py  # Maps tool calls → Python functions
│   ├── memory.py         # Per-session conversation history
│   └── prompts.py        # System prompt
├── bot/
│   └── telegram_bot.py   # Telegram interface
├── core/
│   └── booking_engine.py # All business logic
├── db/
│   ├── models.py         # SQLAlchemy ORM models
│   ├── database.py       # Engine + session management
│   └── seed.py           # Initial equipment data
├── api/
│   └── main.py           # FastAPI app
├── ui/
│   └── index.html        # Single-file web UI
├── config.py             # Environment variable loading
├── main.py               # Entry point
└── requirements.txt
```

---

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Example queries |
| `/clear` | Reset conversation history |
