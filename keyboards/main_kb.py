from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.helpers import is_admin


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Testni boshlash", callback_data="solve_quiz")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Yangi test yaratish", callback_data="create_quiz")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Mening natijalarim", callback_data="my_results")
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="📋 Barcha testlar", callback_data="list_quizzes"),
            InlineKeyboardButton(text="🗑 Test o'chirish", callback_data="delete_quiz"),
        )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()