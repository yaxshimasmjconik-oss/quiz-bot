"""
Guruh rejimi:
- Foydalanuvchi guruhga test yuboradi
- Bot savollarni birma-bir chiqaradi (10 sekund)
- Hamma javob beradi
- Oxirida reyting chiqadi
"""
import asyncio
import random
from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from database import queries
from utils.helpers import score_to_percent, result_emoji

router = Router()

QUESTION_TIME = 10  # sekund


def group_answer_kb(options: list, session_id: int, question_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for i, opt in enumerate(options):
        buttons.append([InlineKeyboardButton(
            text=f"{chr(65 + i)}. {opt['text'][:50]}",
            callback_data=f"gans_{session_id}_{question_id}_{opt['id']}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def run_group_quiz(
    bot: Bot,
    chat_id: int,
    session_id: int,
    quiz_id: int,
    questions: list,
) -> None:
    """Guruh testini boshqaruvchi asosiy funksiya."""

    for q_index, question in enumerate(questions):
        # Sessiya hali faolmi tekshirish
        session = await queries.get_active_session(chat_id)
        if not session or session["id"] != session_id:
            return

        question_id = question["id"]
        options = await queries.get_options(question_id)
        options_list = [dict(o) for o in options]
        random.shuffle(options_list)

        total = len(questions)
        options_text = "\n".join(
            f"  {chr(65+i)}. {o['text']}" for i, o in enumerate(options_list)
        )

        text = (
            f"❓ <b>Savol {q_index + 1}/{total}</b>\n\n"
            f"{question['text']}\n\n"
            f"{options_text}\n\n"
            f"⏱ <b>{QUESTION_TIME} sekund!</b>"
        )

        msg = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=group_answer_kb(options_list, session_id, question_id),
        )

        await queries.update_session_question(session_id, q_index, msg.message_id)

        # Vaqtni hisoblash — har sekund yangilanadi
        for remaining in range(QUESTION_TIME - 1, 0, -1):
            await asyncio.sleep(1)
            session = await queries.get_active_session(chat_id)
            if not session:
                return
            try:
                answerers = await queries.get_question_answerers(session_id, question_id)
                answered_names = ", ".join(
                    f"{'✅' if a['is_correct'] else '❌'} {a['username']}"
                    for a in answerers
                ) if answerers else "Hali hech kim javob bermadi"

                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg.message_id,
                    text=(
                        f"❓ <b>Savol {q_index + 1}/{total}</b>\n\n"
                        f"{question['text']}\n\n"
                        f"{options_text}\n\n"
                        f"⏱ <b>{remaining} sekund qoldi</b>\n\n"
                        f"👥 {answered_names}"
                    ),
                    reply_markup=group_answer_kb(options_list, session_id, question_id),
                )
            except Exception:
                pass

        await asyncio.sleep(1)

        # To'g'ri javobni ko'rsatish
        correct = next((o for o in options_list if o["is_correct"]), None)
        correct_text = correct["text"] if correct else "?"
        answerers = await queries.get_question_answerers(session_id, question_id)
        answered_names = "\n".join(
            f"  {'✅' if a['is_correct'] else '❌'} {a['username']}"
            for a in answerers
        ) if answerers else "  Hech kim javob bermadi"

        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg.message_id,
                text=(
                    f"✅ <b>To'g'ri javob:</b> {correct_text}\n\n"
                    f"<b>Javob berganlar:</b>\n{answered_names}"
                ),
            )
        except Exception:
            pass

        await asyncio.sleep(2)

    # Test tugadi — natijalar
    await queries.end_session(session_id)
    scores = await queries.get_session_scores(session_id)

    if not scores:
        await bot.send_message(chat_id, "🏁 Test tugadi! Hech kim javob bermadi.")
        return

    lines = ["🏆 <b>Test yakunlandi! Natijalar:</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(scores):
        medal = medals[i] if i < 3 else f"{i+1}."
        percent = score_to_percent(row["score"] or 0, row["total"] or 1)
        lines.append(
            f"{medal} <b>{row['username']}</b> — "
            f"{row['score']}/{row['total']} ({percent}%)"
        )

    await bot.send_message(chat_id, "\n".join(lines))


# ── GURUHGA YUBORISH CALLBACK ──────────────────────────────

@router.callback_query(F.data.startswith("gstart_"))
async def cb_group_start(callback: CallbackQuery) -> None:
    """Guruhda test boshlash."""
    quiz_id = int(callback.data.split("_")[1])
    chat_id = callback.message.chat.id

    # Faqat guruhda ishlaydi
    if callback.message.chat.type == "private":
        await callback.answer(
            "❗ Bu tugma faqat guruhda ishlaydi!", show_alert=True
        )
        return

    # Allaqachon faol sessiya bormi
    existing = await queries.get_active_session(chat_id)
    if existing:
        await callback.answer(
            "❗ Guruhda test allaqachon boshlangan!", show_alert=True
        )
        return

    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await callback.answer("Test topilmadi!", show_alert=True)
        return

    questions = await queries.get_questions(quiz_id)
    if not questions:
        await callback.answer("Savollar yo'q!", show_alert=True)
        return

    question_data = [dict(q) for q in questions]
    random.shuffle(question_data)

    session_id = await queries.create_group_session(
        chat_id=chat_id,
        quiz_id=quiz_id,
        started_by=callback.from_user.id,
    )

    username = callback.from_user.first_name or "Foydalanuvchi"
    await callback.message.answer(
        f"🚀 <b>{quiz['title']}</b> testi boshlanmoqda!\n"
        f"▶️ Boshlagan: {username}\n"
        f"❓ Savollar: {len(question_data)} ta\n"
        f"⏱ Har savol: {QUESTION_TIME} sekund\n\n"
        f"Tayyor bo'ling! 3... 2... 1..."
    )
    await callback.answer()

    await asyncio.sleep(3)
    await run_group_quiz(
        bot=callback.bot,
        chat_id=chat_id,
        session_id=session_id,
        quiz_id=quiz_id,
        questions=question_data,
    )


# ── GURUHDA JAVOB BERISH ───────────────────────────────────

@router.callback_query(F.data.startswith("gans_"))
async def cb_group_answer(callback: CallbackQuery) -> None:
    """Guruhda javob berish."""
    parts = callback.data.split("_")
    session_id = int(parts[1])
    question_id = int(parts[2])
    chosen_option_id = int(parts[3])

    user_id = callback.from_user.id
    username = callback.from_user.first_name or f"User{user_id}"

    options = await queries.get_options(question_id)
    correct = next((o for o in options if o["is_correct"]), None)
    is_correct = correct is not None and chosen_option_id == correct["id"]

    saved = await queries.save_group_answer(
        session_id=session_id,
        question_id=question_id,
        user_id=user_id,
        username=username,
        is_correct=is_correct,
    )

    if not saved:
        await callback.answer("❗ Siz allaqachon javob berdingiz!", show_alert=True)
        return

    if is_correct:
        await callback.answer("✅ To'g'ri javob!", show_alert=False)
    else:
        await callback.answer("❌ Noto'g'ri!", show_alert=False)
