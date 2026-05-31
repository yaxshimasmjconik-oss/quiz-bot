from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def quiz_list_kb(quizzes: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for quiz in quizzes:
        label = f"📝 {quiz['title'][:40]} ({quiz['question_count']} savol)"
        builder.row(
            InlineKeyboardButton(
                text=label, callback_data=f"start_quiz_{quiz['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()


def answer_options_kb(options: list, question_id: int, attempt_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.row(
            InlineKeyboardButton(
                text=f"{chr(65 + i)}. {opt['text'][:60]}",
                callback_data=f"answer_{attempt_id}_{question_id}_{opt['id']}",
            )
        )
    return builder.as_markup()


def result_kb(quiz_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔄 Qayta ishlash",
            callback_data=f"start_quiz_{quiz_id}"
        ),
        InlineKeyboardButton(
            text="📤 Guruhga yuborish",
            callback_data=f"share_quiz_{quiz_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()
