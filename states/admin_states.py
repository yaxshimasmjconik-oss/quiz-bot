from aiogram.fsm.state import State, StatesGroup


class CreateQuizSG(StatesGroup):
    waiting_title = State()
    waiting_category = State()
    waiting_question = State()
    waiting_option = State()
    waiting_correct_choice = State()
    confirm_next = State()


class DeleteQuizSG(StatesGroup):
    waiting_quiz_choice = State()


class EditQuizSG(StatesGroup):
    choosing_quiz = State()
    choosing_action = State()
    editing_title = State()
    choosing_question = State()
    editing_question = State()
    choosing_option = State()
    editing_option = State()
    choosing_correct = State()


class CopyQuizSG(StatesGroup):
    choosing_quiz = State()
    waiting_title = State()
