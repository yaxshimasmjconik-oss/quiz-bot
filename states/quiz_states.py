from aiogram.fsm.state import State, StatesGroup


class SolveQuizSG(StatesGroup):
    """Test ishlash uchun holatlar."""
    choosing_quiz = State()   # Quiz tanlash
    answering = State()       # Savollarga javob berish
