from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Testni boshlash", callback_data="solve_quiz")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Yangi test yaratish", callback_data="create_quiz"),
        InlineKeyboardButton(text="📋 Kategoriyalar", callback_data="categories"),
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_quiz"),
        InlineKeyboardButton(text="📋 Nusxalash", callback_data="copy_quiz"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Mening natijalarim", callback_data="my_results"),
        InlineKeyboardButton(text="🏆 Reyting", callback_data="global_rating"),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="🔐 Admin panel", callback_data="admin_panel")
        )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()
