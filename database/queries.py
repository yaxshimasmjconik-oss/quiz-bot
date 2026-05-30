from __future__ import annotations
from typing import Optional
import aiosqlite
from database.db import get_db


async def create_quiz(title: str, created_by: int) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO quizzes (title, created_by) VALUES (?, ?)",
            (title, created_by),
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_quizzes() -> list[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT q.id, q.title, q.created_by, q.created_at,
                   COUNT(DISTINCT qu.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions qu ON qu.quiz_id = q.id
            GROUP BY q.id
            ORDER BY q.created_at DESC
            """
        )
        return await cursor.fetchall()


async def get_quiz(quiz_id: int) -> Optional[aiosqlite.Row]:
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM quizzes WHERE id = ?", (quiz_id,)
        )
        return await cursor.fetchone()


async def delete_quiz(quiz_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM quizzes WHERE id = ?", (quiz_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


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
            INSERT INTO attempt_answers (attempt_id, question_id, chosen_option, is_correct)
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