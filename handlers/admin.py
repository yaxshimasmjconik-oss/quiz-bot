import aiosqlite
from aiogram import Router, F
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from database import queries
from keyboards.admin_kb import (
    correct_answer_kb,
    next_question_kb,
    quiz_list_admin_kb,
    confirm_delete_kb,
)
from keyboards.main_kb import back_to_menu_kb
from states.admin_states import CreateQuizSG, DeleteQuizSG, EditQuizSG, CopyQuizSG
from utils.helpers import is_admin, format_quiz_list

router = Router()


class AdminFilter(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        return user is not None and is_admin(user.id)


# ── KATEGORIYA TANLASH KB ──────────────────────────────────

async def category_kb() -> InlineKeyboardMarkup:
    categories = await queries.get_categories()
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.row(InlineKeyboardButton(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat_{cat['id']}",
        ))
    builder.row(InlineKeyboardButton(
        text="⏭ Kategoriyasiz", callback_data="cat_0"
    ))
    return builder.as_markup()


# ── QUIZ YARATISH ──────────────────────────────────────────

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
    await state.update_data(quiz_title=title)
    await state.set_state(CreateQuizSG.waiting_category)
    await message.answer(
        f"✅ <b>Test nomi:</b> {title}\n\n"
        f"📂 Kategoriyani tanlang:",
        reply_markup=await category_kb(),
    )


@router.callback_query(CreateQuizSG.waiting_category, F.data.startswith("cat_"))
async def cb_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    title = data["quiz_title"]

    quiz_id = await queries.create_quiz(
        title=title,
        created_by=callback.from_user.id,
        category_id=category_id if category_id > 0 else None,
    )
    await state.update_data(quiz_id=quiz_id, question_index=0)
    await state.set_state(CreateQuizSG.waiting_question)
    await callback.message.edit_text(
        f"✅ <b>Test yaratildi:</b> {title}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>1-savol matnini yuboring:</b>"
    )
    await callback.answer()


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


# ── TESTNI NUSXALASH ───────────────────────────────────────

@router.callback_query(F.data == "copy_quiz")
async def cb_copy_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    quizzes = await queries.get_my_quizzes(callback.from_user.id)
    if not quizzes:
        await callback.answer("❗ Nusxalash uchun test yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for q in quizzes:
        builder.row(InlineKeyboardButton(
            text=f"📝 {q['title'][:35]}",
            callback_data=f"copy_select_{q['id']}",
        ))
    builder.row(InlineKeyboardButton(
        text="❌ Bekor qilish", callback_data="main_menu"
    ))

    await state.set_state(CopyQuizSG.choosing_quiz)
    await callback.message.edit_text(
        "📋 <b>Qaysi testni nusxalaysiz?</b>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(CopyQuizSG.choosing_quiz, F.data.startswith("copy_select_"))
async def cb_copy_select(callback: CallbackQuery, state: FSMContext) -> None:
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    await state.update_data(copy_quiz_id=quiz_id)
    await state.set_state(CopyQuizSG.waiting_title)
    await callback.message.edit_text(
        f"📝 <b>{quiz['title'] if quiz else '?'}</b> testini nusxalaysiz.\n\n"
        f"Yangi test nomini kiriting:"
    )
    await callback.answer()


@router.message(CopyQuizSG.waiting_title)
async def msg_copy_title(message: Message, state: FSMContext) -> None:
    new_title = (message.text or "").strip()
    if not new_title:
        await message.answer("❗ Nom bo'sh bo'lmasligi kerak!")
        return

    data = await state.get_data()
    quiz_id = data["copy_quiz_id"]

    new_quiz_id = await queries.copy_quiz(
        quiz_id=quiz_id,
        new_title=new_title,
        user_id=message.from_user.id,
    )
    await state.clear()

    q_count = await queries.count_questions(new_quiz_id)
    await message.answer(
        f"✅ <b>Test nusxalandi!</b>\n\n"
        f"📋 Nomi: <b>{new_title}</b>\n"
        f"❓ Savollar: <b>{q_count} ta</b>",
        reply_markup=back_to_menu_kb(),
    )


# ── TESTNI TAHRIRLASH ──────────────────────────────────────

@router.callback_query(F.data == "edit_quiz")
async def cb_edit_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    quizzes = await queries.get_my_quizzes(callback.from_user.id)
    if not quizzes:
        await callback.answer("❗ Tahrirlash uchun test yo'q!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for q in quizzes:
        builder.row(InlineKeyboardButton(
            text=f"✏️ {q['title'][:35]}",
            callback_data=f"edit_select_{q['id']}",
        ))
    builder.row(InlineKeyboardButton(
        text="❌ Bekor qilish", callback_data="main_menu"
    ))

    await state.set_state(EditQuizSG.choosing_quiz)
    await callback.message.edit_text(
        "✏️ <b>Qaysi testni tahrirlaysiz?</b>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(EditQuizSG.choosing_quiz, F.data.startswith("edit_select_"))
async def cb_edit_select(callback: CallbackQuery, state: FSMContext) -> None:
    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    questions = await queries.get_questions(quiz_id)

    await state.update_data(edit_quiz_id=quiz_id)
    await state.set_state(EditQuizSG.choosing_action)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Nom o'zgartirish",
        callback_data=f"edit_title_{quiz_id}",
    ))
    for i, q in enumerate(questions):
        builder.row(InlineKeyboardButton(
            text=f"❓ {i+1}. {q['text'][:30]}",
            callback_data=f"edit_q_{q['id']}",
        ))
    builder.row(InlineKeyboardButton(
        text="❌ Bekor qilish", callback_data="main_menu"
    ))

    await callback.message.edit_text(
        f"✏️ <b>{quiz['title'] if quiz else '?'}</b>\n\n"
        f"Nima tahrirlaysiz?",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    quiz_id = int(callback.data.split("_")[2])
    await state.update_data(edit_quiz_id=quiz_id)
    await state.set_state(EditQuizSG.editing_title)
    await callback.message.edit_text(
        "✏️ Yangi test nomini kiriting:"
    )
    await callback.answer()


@router.message(EditQuizSG.editing_title)
async def msg_edit_title(message: Message, state: FSMContext) -> None:
    new_title = (message.text or "").strip()
    if not new_title:
        await message.answer("❗ Nom bo'sh bo'lmasligi kerak!")
        return

    data = await state.get_data()
    await queries.update_quiz_title(data["edit_quiz_id"], new_title)
    await state.clear()
    await message.answer(
        f"✅ Test nomi yangilandi: <b>{new_title}</b>",
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data.startswith("edit_q_"))
async def cb_edit_question(callback: CallbackQuery, state: FSMContext) -> None:
    question_id = int(callback.data.split("_")[2])
    options = await queries.get_options(question_id)

    await state.update_data(edit_question_id=question_id)
    await state.set_state(EditQuizSG.choosing_option)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✏️ Savol matnini o'zgartirish",
        callback_data=f"edit_qtext_{question_id}",
    ))
    for opt in options:
        mark = "✅" if opt["is_correct"] else "⬜"
        builder.row(InlineKeyboardButton(
            text=f"{mark} {opt['text'][:35]}",
            callback_data=f"edit_opt_{opt['id']}_{question_id}",
        ))
    builder.row(InlineKeyboardButton(
        text="🔙 Orqaga", callback_data=f"edit_select_{(await state.get_data()).get('edit_quiz_id', 0)}"
    ))

    await callback.message.edit_text(
        "✏️ <b>Nima o'zgartiraysiz?</b>\n\n"
        "<i>✅ — to'g'ri javob</i>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_qtext_"))
async def cb_edit_qtext(callback: CallbackQuery, state: FSMContext) -> None:
    question_id = int(callback.data.split("_")[2])
    await state.update_data(edit_question_id=question_id)
    await state.set_state(EditQuizSG.editing_question)
    await callback.message.edit_text("✏️ Yangi savol matnini kiriting:")
    await callback.answer()


@router.message(EditQuizSG.editing_question)
async def msg_edit_question(message: Message, state: FSMContext) -> None:
    new_text = (message.text or "").strip()
    if not new_text:
        await message.answer("❗ Savol matni bo'sh bo'lmasligi kerak!")
        return
    data = await state.get_data()
    await queries.update_question_text(data["edit_question_id"], new_text)
    await state.clear()
    await message.answer(
        "✅ Savol matni yangilandi!",
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data.startswith("edit_opt_"))
async def cb_edit_option(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("_")
    option_id = int(parts[2])
    question_id = int(parts[3])

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Matnini o'zgartirish",
            callback_data=f"edit_opttext_{option_id}",
        ),
        InlineKeyboardButton(
            text="✅ To'g'ri javob qilish",
            callback_data=f"edit_setcorrect_{option_id}_{question_id}",
        ),
    )
    builder.row(InlineKeyboardButton(
        text="🔙 Orqaga", callback_data=f"edit_q_{question_id}"
    ))

    await callback.message.edit_text(
        "✏️ <b>Variant uchun amal tanlang:</b>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_opttext_"))
async def cb_edit_opttext(callback: CallbackQuery, state: FSMContext) -> None:
    option_id = int(callback.data.split("_")[2])
    await state.update_data(edit_option_id=option_id)
    await state.set_state(EditQuizSG.editing_option)
    await callback.message.edit_text("✏️ Yangi variant matnini kiriting:")
    await callback.answer()


@router.message(EditQuizSG.editing_option)
async def msg_edit_option(message: Message, state: FSMContext) -> None:
    new_text = (message.text or "").strip()
    if not new_text:
        await message.answer("❗ Variant matni bo'sh bo'lmasligi kerak!")
        return
    data = await state.get_data()
    await queries.update_option_text(data["edit_option_id"], new_text)
    await state.clear()
    await message.answer(
        "✅ Variant matni yangilandi!",
        reply_markup=back_to_menu_kb(),
    )


@router.callback_query(F.data.startswith("edit_setcorrect_"))
async def cb_set_correct(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split("_")
    option_id = int(parts[2])
    question_id = int(parts[3])
    await queries.set_correct_option(question_id, option_id)
    await state.clear()
    await callback.message.edit_text(
        "✅ To'g'ri javob o'zgartirildi!",
        reply_markup=back_to_menu_kb(),
    )
    await callback.answer("✅ Saqlandi!")


# ── BARCHA TESTLAR ─────────────────────────────────────────

@router.callback_query(F.data == "list_quizzes")
async def cb_list_quizzes(callback: CallbackQuery) -> None:
    quizzes = await queries.get_all_quizzes()
    text = format_quiz_list([dict(q) for q in quizzes])
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()


# ── TEST O'CHIRISH ─────────────────────────────────────────

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
