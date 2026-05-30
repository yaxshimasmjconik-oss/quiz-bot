import random
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database import queries
from keyboards.quiz_kb import quiz_list_kb, answer_options_kb, result_kb
from keyboards.main_kb import back_to_menu_kb
from states.quiz_states import SolveQuizSG
from utils.helpers import score_to_percent, result_emoji, progress_bar

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

    # Variantlarni aralashtirish
    options_list = [dict(o) for o in options]
    random.shuffle(options_list)

    options_text = "\n".join(
        f"  {chr(65 + i)}. {opt['text']}" for i, opt in enumerate(options_list)
    )
    header = (
        f"❓ <b>Savol {q_index + 1}/{total}</b>\n\n"
        f"{question['text']}\n\n"
        f"{options_text}"
    )

    await callback.message.edit_text(
        header,
        reply_markup=answer_options_kb(options_list, question_id, attempt_id),
    )


# ── QUIZ TANLASH ───────────────────────────────────────────

@router.callback_query(F.data == "solve_quiz")
async def cb_solve_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    quizzes = await queries.get_all_quizzes()
    if not quizzes:
        await callback.message.edit_text(
            "❗ Hozircha hech qanday test mavjud emas.",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(SolveQuizSG.choosing_quiz)
    await callback.message.edit_text(
        "📝 <b>Test tanlang:</b>",
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

    # Savollarni aralashtirish
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
        f"Jami: {total} ta savol\n\n"
        f"Savollar aralashtirildi! Boshlaylik 👇"
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
        feedback = f"✅ <b>To'g'ri!</b>\n<i>{chosen_text}</i>"
    else:
        feedback = (
            f"❌ <b>Noto'g'ri!</b>\n"
            f"Siz: <i>{chosen_text}</i>\n"
            f"To'g'ri: <i>{correct_text}</i>"
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
        percent = score_to_percent(score, total)
        emoji = result_emoji(percent)
        bar = progress_bar(score, total)
        quiz = await queries.get_quiz(data["quiz_id"])
        quiz_title = quiz["title"] if quiz else "Test"

        await state.clear()
        await callback.message.edit_text(
            f"{feedback}\n\n"
            f"{'━' * 20}\n"
            f"{emoji} <b>Test yakunlandi!</b>\n\n"
            f"📋 <b>{quiz_title}</b>\n"
            f"✅ To'g'ri: <b>{score}/{total}</b>\n"
            f"📊 Natija: <b>{percent}%</b>\n"
            f"{bar}",
            reply_markup=result_kb(),
        )

    await callback.answer("✅ To'g'ri!" if is_correct else "❌ Noto'g'ri!")


# ── NATIJALAR ──────────────────────────────────────────────

@router.callback_query(F.data == "my_results")
async def cb_my_results(callback: CallbackQuery) -> None:
    attempts = await queries.get_user_attempts(callback.from_user.id)

    if not attempts:
        await callback.message.edit_text(
            "📊 <b>Mening natijalarim</b>\n\n"
            "Hali hech qanday test ishlamadingiz.\n"
            "Boshlang! 🚀",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer()
        return

    lines = ["📊 <b>Mening natijalarim:</b>\n"]
    for i, a in enumerate(attempts, 1):
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