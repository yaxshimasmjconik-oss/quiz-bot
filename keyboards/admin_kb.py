from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import MAX_OPTIONS, MIN_OPTIONS


def options_action_kb(option_count: int) -> InlineKeyboardMarkup:
    """Variant qo'shish yoki to'g'ri javobni tanlash tugmalari."""
    builder = InlineKeyboardBuilder()
    if option_count < MAX_OPTIONS:
        builder.row(
            InlineKeyboardButton(
                text="➕ Variant qo'shish", callback_data="add_option"
            )
        )
    if option_count >= MIN_OPTIONS:
        builder.row(
            InlineKeyboardButton(
                text="✅ To'g'ri javobni tanlash", callback_data="choose_correct"
            )
        )
    return builder.as_markup()


def correct_answer_kb(options: list[dict]) -> InlineKeyboardMarkup:
    """To'g'ri javobni tanlash uchun tugmalar."""
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.row(
            InlineKeyboardButton(
                text=f"{chr(65 + i)}. {opt['text'][:40]}",
                callback_data=f"correct_{opt['id']}",
            )
        )
    return builder.as_markup()


def next_question_kb() -> InlineKeyboardMarkup:
    """Keyingi savol yoki testni yakunlash."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="➕ Yana savol qo'shish", callback_data="add_more_question"
        ),
        InlineKeyboardButton(
            text="✔️ Testni saqlash", callback_data="save_quiz"
        ),
    )
    return builder.as_markup()


def quiz_list_admin_kb(quizzes: list) -> InlineKeyboardMarkup:
    """Admin uchun quiz ro'yxati (o'chirish uchun)."""
    builder = InlineKeyboardBuilder()
    for quiz in quizzes:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {quiz['title'][:35]} ({quiz['question_count']} savol)",
                callback_data=f"del_quiz_{quiz['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="main_menu")
    )
    return builder.as_markup()


def confirm_delete_kb(quiz_id: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Ha, o'chir", callback_data=f"confirm_del_{quiz_id}"
        ),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="delete_quiz"),
    )
    return builder.as_markup()
