from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshiradi."""
    return user_id in ADMIN_IDS


def score_to_percent(score: int, total: int) -> float:
    """Ball foizini hisoblaydi."""
    if total == 0:
        return 0.0
    return round(score / total * 100, 1)


def result_emoji(percent: float) -> str:
    """Foizga qarab emoji qaytaradi."""
    if percent >= 90:
        return "🏆"
    elif percent >= 70:
        return "🌟"
    elif percent >= 50:
        return "👍"
    else:
        return "📚"


def progress_bar(score: int, total: int, length: int = 10) -> str:
    """Matnli progress bar yaratadi."""
    filled = round(score / total * length) if total else 0
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


def format_quiz_list(quizzes: list) -> str:
    """Quiz ro'yxatini chiroyli formatda qaytaradi."""
    if not quizzes:
        return "❗ Hech qanday test topilmadi."
    lines = ["📋 <b>Barcha testlar:</b>\n"]
    for i, q in enumerate(quizzes, 1):
        lines.append(
            f"{i}. <b>{q['title']}</b>\n"
            f"   📌 {q['question_count']} ta savol\n"
            f"   🕒 {q['created_at'][:16]}\n"
        )
    return "\n".join(lines)
