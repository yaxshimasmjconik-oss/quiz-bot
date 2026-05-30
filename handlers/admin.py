import aiosqlite
from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
from database import queries
from keyboards.admin_kb import (
    correct_answer_kb,
    next_question_kb,
    quiz_list_admin_kb,
    confirm_delete_kb,
)
from keyboards.main_kb import back_to_menu_kb
from states.admin_states import CreateQuizSG, DeleteQuizSG
from utils.helpers import is_admin, format_quiz_list

router = Router()


class AdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and is_admin(user.id)


# ── QUIZ YARATISH (hammaga ochiq) ──────────────────────────

@router.callback_query(F.data == "create_quiz")
async def cb_create_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CreateQuizSG.waiting_title)
    await callback.message.edit_text(
        "📝 <b>Yangi test yaratish</b>\n\n"
        "Test nomini kiriting:\n"
        "<i>Masalan: Python asoslari</i>",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer()


@router.message(CreateQuizSG.waiting_title)
async def msg_quiz_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("❗ Test nomini kiriting.")
        return
    quiz_id = await queries.create_quiz(title=title, created_by=message.from_user.id)
    await state.update_data(quiz_id=quiz_id, question_index=0)
    await state.set_state(CreateQuizSG.waiting_question)
    await message.answer(
        f"✅ <b>Test yaratildi:</b> {title}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>1-savol matnini yuboring:</b>"
    )


@router.message(CreateQuizSG.waiting_question)
async def msg_question_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("❗ Savol matni bo'sh bo'lmasligi kerak.")
        return

    data = await state.get_data()
    q_index: int = data.get("question_index", 0)
    quiz_id: int = data["quiz_id"]

    question_id = await queries.add_question(
        quiz_id=quiz_id, text=text, position=q_index
    )
    await state.update_data(
        current_question_id=question_id,
        current_options=[],
        question_index=q_index + 1,
    )
    await state.set_state(CreateQuizSG.waiting_option)
    await message.answer(
        f"✅ Savol qabul qilindi!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Variantlarni yuboring (har biri alohida qatorda):\n\n"
        f"<code>Variant A\n"
        f"Variant B\n"
        f"Variant C\n"
        f"Variant D</code>"
    )


@router.message(CreateQuizSG.waiting_option)
async def msg_options(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if len(lines) < 2:
        await message.answer(
            "❗ Kamida <b>2 ta variant</b> kiriting!\n\n"
            "<code>Variant A\nVariant B</code>"
        )
        return

    if len(lines) > 10:
        await message.answer("❗ Ko'pi bilan <b>10 ta variant</b>!")
        return

    data = await state.get_data()
    question_id: int = data["current_question_id"]

    saved_options = []
    for opt_text in lines:
        opt_id = await queries.add_option(
            question_id=question_id, text=opt_text, is_correct=False
        )
        saved_options.append({"id": opt_id, "text": opt_text})

    await state.update_data(current_options=saved_options)
    await state.set_state(CreateQuizSG.waiting_correct_choice)

    options_preview = "\n".join(
        f"  {chr(65+i)}. {o['text']}" for i, o in enumerate(saved_options)
    )
    await message.answer(
        f"✅ <b>{len(saved_options)} ta variant:</b>\n\n"
        f"{options_preview}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>To'g'ri javobni tanlang:</b>",
        reply_markup=correct_answer_kb(saved_options),
    )


@router.callback_query(
    CreateQuizSG.waiting_correct_choice,
    F.data.startswith("correct_"),
)
async def cb_correct_selected(callback: CallbackQuery, state: FSMContext) -> None:
    correct_option_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    options: list = data.get("current_options", [])

    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "UPDATE options SET is_correct = 1 WHERE id = ?",
            (correct_option_id,),
        )
        await db.commit()

    correct_text = next(
        (o["text"] for o in options if o["id"] == correct_option_id), "?"
    )
    q_index = data.get("question_index", 1)

    await state.set_state(CreateQuizSG.confirm_next)
    await callback.message.edit_text(
        f"✅ <b>To'g'ri javob:</b> {correct_text}\n\n"
        f"Jami {q_index} ta savol kiritildi.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Nima qilmoqchisiz?",
        reply_markup=next_question_kb(),
    )
    await callback.answer()


@router.callback_query(CreateQuizSG.confirm_next, F.data == "add_more_question")
async def cb_add_more_question(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    q_index = data.get("question_index", 1)
    await state.set_state(CreateQuizSG.waiting_question)
    await callback.message.edit_text(
        f"📌 <b>{q_index + 1}-savol matnini yuboring:</b>"
    )
    await callback.answer()


@router.callback_query(CreateQuizSG.confirm_next, F.data == "save_quiz")
async def cb_save_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_id: int = data["quiz_id"]
    q_count = await queries.count_questions(quiz_id)
    quiz = await queries.get_quiz(quiz_id)
    await state.clear()
    await callback.message.edit_text(
        f"🎉 <b>Test saqlandi!</b>\n\n"
        f"📋 Nomi: <b>{quiz['title'] if quiz else '?'}</b>\n"
        f"❓ Savollar: <b>{q_count} ta</b>\n\n"
        f"Foydalanuvchilar uchun tayyor! ✅",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer("✅ Saqlandi!")


# ── BARCHA TESTLAR (hammaga ochiq) ─────────────────────────

@router.callback_query(F.data == "list_quizzes")
async def cb_list_quizzes(callback: CallbackQuery) -> None:
    quizzes = await queries.get_all_quizzes()
    text = format_quiz_list([dict(q) for q in quizzes])
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()


# ── TEST O'CHIRISH (faqat admin) ───────────────────────────

@router.callback_query(F.data == "delete_quiz")
async def cb_delete_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Faqat admin o'chira oladi!", show_alert=True)
        return
    quizzes = await queries.get_all_quizzes()
    if not quizzes:
        await callback.answer("❗ O'chirish uchun test topilmadi.", show_alert=True)
        return
    await state.set_state(DeleteQuizSG.waiting_quiz_choice)
    await callback.message.edit_text(
        "🗑 <b>Qaysi testni o'chirmoqchisiz?</b>",
        reply_markup=quiz_list_admin_kb([dict(q) for q in quizzes]),
    )
    await callback.answer()


@router.callback_query(
    DeleteQuizSG.waiting_quiz_choice,
    F.data.startswith("del_quiz_"),
)
async def cb_del_quiz_confirm(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Faqat admin!", show_alert=True)
        return
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await callback.answer("Test topilmadi!", show_alert=True)
        return
    await callback.message.edit_text(
        f"⚠️ <b>Rostdan ham o'chirasizmi?</b>\n\n"
        f"Test: <b>{quiz['title']}</b>",
        reply_markup=confirm_delete_kb(quiz_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_"))
async def cb_confirm_delete(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Faqat admin!", show_alert=True)
        return
    quiz_id = int(callback.data.split("_")[2])
    deleted = await queries.delete_quiz(quiz_id)
    await state.clear()
    if deleted:
        await callback.message.edit_text(
            "✅ Test o'chirildi!",
            reply_markup=back_to_menu_kb(),
        )
        await callback.answer("O'chirildi!")
    else:
        await callback.answer("❗ Test topilmadi.", show_alert=True)