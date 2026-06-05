import random
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import queries
from keyboards.quiz_kb import quiz_list_kb, answer_options_kb, result_kb
from keyboards.main_kb import back_to_menu_kb
from states.quiz_states import SolveQuizSG
from utils.helpers import (
    score_to_percent, result_emoji, progress_bar,
    result_message, question_card, achievement_check
)

router = Router()


async def _send_question(
    callback: CallbackQuery,
    attempt_id: int,
    questions: list,
    q_index: int,
) -> None:
    question = questions[q_index]
    question_id = question["id"]
    options = await queries.get_options(question_id)
    total = len(questions)
    options_list = [dict(o) for o in options]
    random.shuffle(options_list)

    await callback.message.edit_text(
        question_card(q_index, total, question["text"], options_list),
        reply_markup=answer_options_kb(options_list, question_id, attempt_id),
    )


# ── DEEP LINK ──────────────────────────────────────────────

@router.message(CommandStart(deep_link=True))
async def cmd_start_deep(message: Message, state: FSMContext) -> None:
    args = message.text.split()
    if len(args) < 2:
        return
    param = args[1]
    if not param.startswith("quiz_"):
        return
    try:
        quiz_id = int(param.split("_")[1])
    except (ValueError, IndexError):
        return

    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await message.answer("❗ Test topilmadi!")
        return

    questions = await queries.get_questions(quiz_id)
    if not questions:
        await message.answer("❗ Bu testda savollar yo'q!")
        return

    await queries.register_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
    )

    question_data = [dict(q) for q in questions]
    random.shuffle(question_data)
    total = len(question_data)

    attempt_id = await queries.create_attempt(
        user_id=message.from_user.id,
        quiz_id=quiz_id,
        total=total,
    )

    await state.set_state(SolveQuizSG.answering)
    await state.update_data(
        attempt_id=attempt_id,
        quiz_id=quiz_id,
        questions=question_data,
        current_index=0,
    )

    msg = await message.answer(
        f"🚀 <b>{quiz['title']}</b>\n"
        f"❓ Jami: {total} ta savol\n\n"
        f"Boshlaylik! 👇"
    )

    class FakeCallback:
        def __init__(self, m):
            self.message = m
            self.from_user = message.from_user
            self.bot = message.bot
        async def answer(self, *a, **kw): pass

    await _send_question(FakeCallback(msg), attempt_id, question_data, 0)


# ── KATEGORIYALAR ──────────────────────────────────────────

@router.callback_query(F.data == "categories")
async def cb_categories(callback: CallbackQuery) -> None:
    categories = await queries.get_categories()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat_browse_{cat['id']}",
        ))
    builder.row(InlineKeyboardButton(
        text="🏠 Bosh menyu", callback_data="main_menu"
    ))
    await callback.message.edit_text(
        "📂 <b>Kategoriyalar</b>\n\nQaysi mavzuni ko'rmoqchisiz?",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_browse_"))
async def cb_cat_browse(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split("_")[2])
    quizzes = await queries.get_quizzes_by_category(category_id)
    categories = await queries.get_categories()
    cat = next((c for c in categories if c["id"] == category_id), None)
    cat_name = f"{cat['emoji']} {cat['name']}" if cat else "Kategoriya"

    if not quizzes:
        await callback.message.edit_text(
            f"{cat_name}\n\n❗ Bu kategoriyada testlar yo'q.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(SolveQuizSG.choosing_quiz)
    await callback.message.edit_text(
        f"{cat_name}\n\n📝 <b>Testni tanlang:</b>",
        reply_markup=quiz_list_kb([dict(q) for q in quizzes]),
    )
    await callback.answer()


# ── QUIZ TANLASH ───────────────────────────────────────────

@router.callback_query(F.data == "solve_quiz")
async def cb_solve_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    quizzes = await queries.get_my_quizzes(callback.from_user.id)
    if not quizzes:
        await callback.message.edit_text(
            "📭 <b>Sizda hali test yo'q!</b>\n\n"
            "➕ Yangi test yarating!",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(SolveQuizSG.choosing_quiz)
    await callback.message.edit_text(
        f"📝 <b>Qaysi testni ishlaysiz?</b>\n\n"
        f"Jami: {len(quizzes)} ta test mavjud",
        reply_markup=quiz_list_kb([dict(q) for q in quizzes]),
    )
    await callback.answer()


@router.callback_query(SolveQuizSG.choosing_quiz, F.data.startswith("start_quiz_"))
async def cb_start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await callback.answer("Test topilmadi!", show_alert=True)
        return

    questions = await queries.get_questions(quiz_id)
    if not questions:
        await callback.answer("Bu testda savollar yo'q!", show_alert=True)
        return

    question_data = [dict(q) for q in questions]
    random.shuffle(question_data)
    total = len(question_data)

    attempt_id = await queries.create_attempt(
        user_id=callback.from_user.id,
        quiz_id=quiz_id,
        total=total,
    )

    await state.set_state(SolveQuizSG.answering)
    await state.update_data(
        attempt_id=attempt_id,
        quiz_id=quiz_id,
        questions=question_data,
        current_index=0,
    )

    await callback.message.edit_text(
        f"🚀 <b>{quiz['title']}</b>\n"
        f"❓ Jami: {total} ta savol\n\n"
        f"Boshlaylik! 👇"
    )
    await _send_question(callback, attempt_id, question_data, 0)
    await callback.answer()


# ── JAVOB BERISH ───────────────────────────────────────────

@router.callback_query(SolveQuizSG.answering, F.data.startswith("answer_"))
async def cb_answer(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("_")
    attempt_id = int(parts[1])
    question_id = int(parts[2])
    chosen_option_id = int(parts[3])

    data = await state.get_data()
    if data.get("attempt_id") != attempt_id:
        await callback.answer("Bu savol siz uchun emas!", show_alert=True)
        return

    questions: list = data["questions"]
    current_index: int = data["current_index"]

    options = await queries.get_options(question_id)
    correct_option = next((o for o in options if o["is_correct"]), None)
    is_correct = correct_option is not None and chosen_option_id == correct_option["id"]

    await queries.save_answer(attempt_id, question_id, chosen_option_id, is_correct)

    chosen_text = next((o["text"] for o in options if o["id"] == chosen_option_id), "?")
    correct_text = correct_option["text"] if correct_option else "?"

    if is_correct:
        await callback.answer("✅ To'g'ri!", show_alert=True)
        feedback = f"✅ <b>To'g'ri javob!</b>\n\n📌 {chosen_text}"
    else:
        await callback.answer(
            f"❌ Noto'g'ri!\nTo'g'ri javob: {correct_text}",
            show_alert=True
        )
        feedback = (
            f"❌ <b>Noto'g'ri!</b>\n\n"
            f"Siz: <i>{chosen_text}</i>\n"
            f"✅ To'g'ri: <b>{correct_text}</b>"
        )

    next_index = current_index + 1

    if next_index < len(questions):
        await state.update_data(current_index=next_index)
        await callback.message.edit_text(feedback)
        await _send_question(callback, attempt_id, questions, next_index)
    else:
        await queries.finish_attempt(attempt_id)
        result = await queries.get_attempt_result(attempt_id)
        score = result["score"] if result else 0
        total = result["total"] if result else len(questions)
        quiz = await queries.get_quiz(data["quiz_id"])
        quiz_title = quiz["title"] if quiz else "Test"

        user_attempts = await queries.get_user_attempts(callback.from_user.id)
        total_games = len(user_attempts)
        achievement = achievement_check(score, total, total_games)

        result_text = result_message(score, total, quiz_title)
        if achievement:
            result_text += f"\n\n{achievement}"

        await state.clear()
        await callback.message.edit_text(
            result_text,
            reply_markup=result_kb(data["quiz_id"]),
        )


# ── SAVOL STATISTIKASI ─────────────────────────────────────

@router.callback_query(F.data.startswith("quiz_stats_"))
async def cb_quiz_stats(callback: CallbackQuery) -> None:
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    stats = await queries.get_question_stats(quiz_id)

    if not stats:
        await callback.answer("Statistika yo'q!", show_alert=True)
        return

    lines = [f"📊 <b>{quiz['title'] if quiz else '?'} — Statistika</b>\n"]
    for i, s in enumerate(stats, 1):
        total = s["total_answers"] or 0
        correct = s["correct_answers"] or 0
        percent = round(correct / total * 100) if total else 0
        bar_filled = round(percent / 10)
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        lines.append(
            f"{i}. {s['question_text'][:40]}\n"
            f"   [{bar}] {percent}% ({correct}/{total})\n"
        )

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


# ── GURUHGA YUBORISH ───────────────────────────────────────

@router.callback_query(F.data.startswith("share_quiz_"))
async def cb_share_quiz(callback: CallbackQuery) -> None:
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await callback.answer("Test topilmadi!", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username
    deep_link = f"https://t.me/{bot_username}?start=quiz_{quiz_id}"

    await callback.message.answer(
        f"📤 <b>{quiz['title']}</b> testini ulashing!\n\n"
        f"🔗 Havola: {deep_link}",
    )
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            f"📝 <b>{quiz['title']}</b>\n\n"
            f"✅ Testni ishlash uchun tugmani bosing!\n"
            f"👥 Guruhda birga ishlash uchun forward qiling!"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="▶️ Testni boshlash",
                url=deep_link,
            )],
            [InlineKeyboardButton(
                text="👥 Guruhda boshlash",
                callback_data=f"gstart_{quiz_id}",
            )]
        ])
    )
    await callback.answer("✅ Ulashish uchun xabar yuborildi!")


# ── NATIJALAR ──────────────────────────────────────────────

@router.callback_query(F.data == "my_results")
async def cb_my_results(callback: CallbackQuery) -> None:
    attempts = await queries.get_user_attempts(callback.from_user.id)

    if not attempts:
        await callback.message.edit_text(
            "📊 <b>Mening natijalarim</b>\n\n"
            "📭 Hali hech qanday test ishlamadingiz.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    lines = ["📊 <b>Mening natijalarim:</b>\n"]
    for i, a in enumerate(attempts[:10], 1):
        percent = score_to_percent(a["score"], a["total"])
        emoji = result_emoji(percent)
        finished = (a["finished_at"] or "")[:16]
        lines.append(
            f"{i}. {emoji} <b>{a['title']}</b>\n"
            f"   ✅ {a['score']}/{a['total']} — <b>{percent}%</b>\n"
            f"   🕒 {finished}\n"
        )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()
