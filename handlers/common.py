from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.main_kb import main_menu_kb
from utils.helpers import is_admin

router = Router()

WELCOME_TEXT = (
    "👋 <b>Quiz Botga xush kelibsiz!</b>\n\n"
    "Bu bot orqali siz turli mavzulardagi testlarni ishlashingiz mumkin.\n\n"
    "Quyidagi menyudan birini tanlang:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Botni ishga tushirish va asosiy menyuni ko'rsatish."""
    await state.clear()
    admin = is_admin(message.from_user.id)  # type: ignore[union-attr]
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_kb(is_admin=admin),
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Asosiy menyuga qaytish."""
    await state.clear()
    admin = is_admin(callback.from_user.id)
    await callback.message.edit_text(  # type: ignore[union-attr]
        WELCOME_TEXT,
        reply_markup=main_menu_kb(is_admin=admin),
    )
    await callback.answer()
