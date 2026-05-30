import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi topilmadi! .env faylini tekshiring.")

_admin_ids_raw: str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [
    int(uid.strip())
    for uid in _admin_ids_raw.split(",")
    if uid.strip().isdigit()
]

DB_PATH: str = os.getenv("DB_PATH", "quiz_bot.db")

MAX_OPTIONS: int = 10
MIN_OPTIONS: int = 2
