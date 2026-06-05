import aiosqlite
from config import DB_PATH

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    emoji       TEXT    NOT NULL DEFAULT '📝'
);

CREATE TABLE IF NOT EXISTS quizzes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    created_by  INTEGER NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text        TEXT    NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    text        TEXT    NOT NULL,
    is_correct  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    quiz_id     INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    score       INTEGER NOT NULL DEFAULT 0,
    total       INTEGER NOT NULL DEFAULT 0,
    started_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME
);

CREATE TABLE IF NOT EXISTS attempt_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id      INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
    question_id     INTEGER NOT NULL,
    chosen_option   INTEGER NOT NULL,
    is_correct      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS group_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id         INTEGER NOT NULL,
    quiz_id         INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    started_by      INTEGER NOT NULL,
    current_q_index INTEGER NOT NULL DEFAULT 0,
    message_id      INTEGER,
    is_active       INTEGER NOT NULL DEFAULT 1,
    question_time   INTEGER NOT NULL DEFAULT 10,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS group_answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES group_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    username    TEXT,
    is_correct  INTEGER NOT NULL DEFAULT 0,
    answered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, question_id, user_id)
);

CREATE TABLE IF NOT EXISTS global_ratings (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    total_score INTEGER NOT NULL DEFAULT 0,
    total_games INTEGER NOT NULL DEFAULT 0,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_CATEGORIES = [
    ("Fanlar", "🔬"),
    ("Tarix", "📜"),
    ("Matematika", "🔢"),
    ("IT va Texnologiya", "💻"),
    ("Sport", "⚽"),
    ("Musiqa", "🎵"),
    ("Geografiya", "🌍"),
    ("Boshqa", "📝"),
]


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        # Default kategoriyalarni qo'shish
        for name, emoji in DEFAULT_CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO categories (name, emoji) VALUES (?, ?)",
                (name, emoji),
            )
        await db.commit()


class get_db:
    def __init__(self):
        self._conn = None

    async def __aenter__(self) -> aiosqlite.Connection:
        self._conn = await aiosqlite.connect(DB_PATH)
        self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            await self._conn.close()
