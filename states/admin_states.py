from aiogram.fsm.state import State, StatesGroup


class CreateQuizSG(StatesGroup):
    """Quiz yaratish uchun holatlar."""
    waiting_title = State()          # Quiz nomini kutish
    waiting_question = State()       # Savol matnini kutish
    waiting_option = State()         # Javob variantini kutish
    waiting_correct_choice = State() # To'g'ri javobni tanlashni kutish
    confirm_next = State()           # Savol qo'shishni davom ettirishni tasdiqlash


class DeleteQuizSG(StatesGroup):
    """Quiz o'chirish uchun holatlar."""
    waiting_quiz_choice = State()
