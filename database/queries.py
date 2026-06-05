from __future__ import annotations
from typing import Optional
import aiosqlite
from database.db import get_db


# ── KATEGORIYALAR ──────────────────────────────────────────

async def get_categories() -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM categories ORDER BY id")
        return await cursor.fetchall()


# ── QUIZLAR ────────────────────────────────────────────────

async def create_quiz(
    title: str, created_by: int, category_id: Optional[int] = None
) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO quizzes (title, created_by, category_id) VALUES (?, ?, ?)",
            (title, created_by, category_id),
        )
        await db.commit()
        return cursor.lastrowid


async def get_my_quizzes(user_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.id, q.title, q.created_by, q.created_at,
                   COUNT(DISTINCT qu.id) AS question_count,
                   c.name as category_name, c.emoji as category_emoji
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            LEFT JOIN categories c ON c.id = q.category_id
            WHERE q.created_by = ?
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """,
            (user_id,),
        )
        return await cursor.fetchall()


async def get_quizzes_by_category(category_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.id, q.title, q.created_by, q.created_at,
                   COUNT(DISTINCT qu.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            WHERE q.category_id = ?
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """,
            (category_id,),
        )
        return await cursor.fetchall()


async def get_all_quizzes() -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.id, q.title, q.created_by, q.created_at,
                   COUNT(DISTINCT qu.id) AS question_count,
                   c.name as category_name, c.emoji as category_emoji
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            LEFT JOIN categories c ON c.id = q.category_id
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """
        )
        return await cursor.fetchall()


async def get_quiz(quiz_id: int) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.*, c.name as category_name, c.emoji as category_emoji
            FROM quizzes q
            LEFT JOIN categories c ON c.id = q.category_id
            WHERE q.id = ?
            """,
            (quiz_id,),
        )
        return await cursor.fetchone()


async def delete_quiz(quiz_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM quizzes WHERE id = ?", (quiz_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def copy_quiz(quiz_id: int, new_title: str, user_id: int) -> int:
    """Testni nusxalash."""
    async with get_db() as db:
        # Asl testni olish
        cursor = await db.execute(
            "SELECT * FROM quizzes WHERE id = ?", (quiz_id,)
        )
        quiz = await cursor.fetchone()
        if not quiz:
            return 0

        # Yangi test yaratish
        cursor = await db.execute(
            "INSERT INTO quizzes (title, created_by, category_id) VALUES (?, ?, ?)",
            (new_title, user_id, quiz["category_id"]),
        )
        new_quiz_id = cursor.lastrowid

        # Savollarni nusxalash
        cursor = await db.execute(
            "SELECT * FROM questions WHERE quiz_id = ? ORDER BY position",
            (quiz_id,),
        )
        questions = await cursor.fetchall()

        for q in questions:
            cursor = await db.execute(
                "INSERT INTO questions (quiz_id, text, position) VALUES (?, ?, ?)",
                (new_quiz_id, q["text"], q["position"]),
            )
            new_q_id = cursor.lastrowid

            # Variantlarni nusxalash
            cursor2 = await db.execute(
                "SELECT * FROM options WHERE question_id = ?", (q["id"],)
            )
            options = await cursor2.fetchall()
            for opt in options:
                await db.execute(
                    "INSERT INTO options (question_id, text, is_correct) VALUES (?, ?, ?)",
                    (new_q_id, opt["text"], opt["is_correct"]),
                )

        await db.commit()
        return new_quiz_id


async def update_quiz_title(quiz_id: int, new_title: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE quizzes SET title = ? WHERE id = ?",
            (new_title, quiz_id),
        )
        await db.commit()


async def update_question_text(question_id: int, new_text: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE questions SET text = ? WHERE id = ?",
            (new_text, question_id),
        )
        await db.commit()


async def update_option_text(option_id: int, new_text: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE options SET text = ? WHERE id = ?",
            (new_text, option_id),
        )
        await db.commit()


async def set_correct_option(question_id: int, option_id: int) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE options SET is_correct = 0 WHERE question_id = ?",
            (question_id,),
        )
        await db.execute(
            "UPDATE options SET is_correct = 1 WHERE id = ?",
            (option_id,),
        )
        await db.commit()


# ── SAVOLLAR ───────────────────────────────────────────────

async def add_question(quiz_id: int, text: str, position: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO questions (quiz_id, text, position) VALUES (?, ?, ?)",
            (quiz_id, text, position),
        )
        await db.commit()
        return cursor.lastrowid


async def get_questions(quiz_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM questions WHERE quiz_id = ? ORDER BY position",
            (quiz_id,),
        )
        return await cursor.fetchall()


async def count_questions(quiz_id: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM questions WHERE quiz_id = ?", (quiz_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ── VARIANTLAR ─────────────────────────────────────────────

async def add_option(question_id: int, text: str, is_correct: bool = False) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO options (question_id, text, is_correct) VALUES (?, ?, ?)",
            (question_id, text, int(is_correct)),
        )
        await db.commit()
        return cursor.lastrowid


async def get_options(question_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM options WHERE question_id = ? ORDER BY id",
            (question_id,),
        )
        return await cursor.fetchall()


async def count_options(question_id: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM options WHERE question_id = ?", (question_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


# ── URINISHLAR ─────────────────────────────────────────────

async def create_attempt(user_id: int, quiz_id: int, total: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO attempts (user_id, quiz_id, total) VALUES (?, ?, ?)",
            (user_id, quiz_id, total),
        )
        await db.commit()
        return cursor.lastrowid


async def save_answer(
    attempt_id: int, question_id: int, chosen_option: int, is_correct: bool
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO attempt_answers
            (attempt_id, question_id, chosen_option, is_correct)
            VALUES (?, ?, ?, ?)
            """,
            (attempt_id, question_id, chosen_option, int(is_correct)),
        )
        if is_correct:
            await db.execute(
                "UPDATE attempts SET score = score + 1 WHERE id = ?",
                (attempt_id,),
            )
        await db.commit()


async def finish_attempt(attempt_id: int) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE attempts SET finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (attempt_id,),
        )
        await db.commit()


async def get_attempt_result(attempt_id: int) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT score, total FROM attempts WHERE id = ?", (attempt_id,)
        )
        return await cursor.fetchone()


async def get_user_attempts(user_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT a.id, q.title, a.score, a.total, a.finished_at
            FROM attempts a
            JOIN quizzes q ON q.id = a.quiz_id
            WHERE a.user_id = ? AND a.finished_at IS NOT NULL
            ORDER BY a.finished_at DESC
            """,
            (user_id,),
        )
        return await cursor.fetchall()


async def get_question_stats(quiz_id: int) -> list[aiosqlite.Row]:
    """Har bir savol uchun statistika."""
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT
                q.text as question_text,
                COUNT(aa.id) as total_answers,
                SUM(aa.is_correct) as correct_answers
            FROM questions q
            LEFT JOIN attempt_answers aa ON aa.question_id = q.id
            WHERE q.quiz_id = ?
            GROUP BY q.id
            ORDER BY q.position
            """,
            (quiz_id,),
        )
        return await cursor.fetchall()


# ── FOYDALANUVCHILAR ───────────────────────────────────────

async def register_user(user_id: int, username: str, full_name: str) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen = CURRENT_TIMESTAMP
            """,
            (user_id, username, full_name),
        )
        await db.commit()


async def get_all_users() -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        )
        return await cursor.fetchall()


async def get_stats() -> dict:
    async with get_db() as db:
        users = (await (await db.execute(
            "SELECT COUNT(*) FROM users")).fetchone())[0]
        quizzes = (await (await db.execute(
            "SELECT COUNT(*) FROM quizzes")).fetchone())[0]
        attempts = (await (await db.execute(
            "SELECT COUNT(*) FROM attempts WHERE finished_at IS NOT NULL"
        )).fetchone())[0]
        return {"users": users, "quizzes": quizzes, "attempts": attempts}


async def get_all_user_ids() -> list[int]:
    async with get_db() as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


# ── GURUH SESSIYALARI ──────────────────────────────────────

async def create_group_session(
    chat_id: int, quiz_id: int, started_by: int, question_time: int = 10
) -> int:
    async with get_db() as db:
        await db.execute(
            "UPDATE group_sessions SET is_active = 0 WHERE chat_id = ?",
            (chat_id,),
        )
        cursor = await db.execute(
            """
            INSERT INTO group_sessions
            (chat_id, quiz_id, started_by, question_time)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, quiz_id, started_by, question_time),
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_session(chat_id: int) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT * FROM group_sessions
            WHERE chat_id = ? AND is_active = 1
            ORDER BY created_at DESC LIMIT 1
            """,
            (chat_id,),
        )
        return await cursor.fetchone()


async def update_session_question(
    session_id: int, q_index: int, message_id: int
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            UPDATE group_sessions
            SET current_q_index = ?, message_id = ?
            WHERE id = ?
            """,
            (q_index, message_id, session_id),
        )
        await db.commit()


async def end_session(session_id: int) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE group_sessions SET is_active = 0 WHERE id = ?",
            (session_id,),
        )
        await db.commit()


async def save_group_answer(
    session_id: int,
    question_id: int,
    user_id: int,
    username: str,
    is_correct: bool,
) -> bool:
    async with get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO group_answers
                (session_id, question_id, user_id, username, is_correct)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, question_id, user_id, username, int(is_correct)),
            )
            await db.commit()
            return True
        except Exception:
            return False


async def get_session_scores(session_id: int) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT username, user_id, COUNT(*) as total, SUM(is_correct) as score
            FROM group_answers
            WHERE session_id = ?
            GROUP BY user_id
            ORDER BY score DESC
            """,
            (session_id,),
        )
        return await cursor.fetchall()


async def get_question_answerers(
    session_id: int, question_id: int
) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT username, is_correct FROM group_answers
            WHERE session_id = ? AND question_id = ?
            ORDER BY answered_at
            """,
            (session_id, question_id),
        )
        return await cursor.fetchall()


# ── GLOBAL REYTING ─────────────────────────────────────────

async def update_global_rating(
    user_id: int, username: str, score: int
) -> None:
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO global_ratings (user_id, username, total_score, total_games)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                total_score = total_score + excluded.total_score,
                total_games = total_games + 1,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, username, score),
        )
        await db.commit()


async def get_global_rating(limit: int = 10) -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT username, total_score, total_games
            FROM global_ratings
            ORDER BY total_score DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()
