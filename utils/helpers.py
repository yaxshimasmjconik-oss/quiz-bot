from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def score_to_percent(score: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(score / total * 100, 1)


def result_emoji(percent: float) -> str:
    if percent == 100:
        return "🏆"
    elif percent >= 90:
        return "🌟"
    elif percent >= 70:
        return "👍"
    elif percent >= 50:
        return "📚"
    else:
        return "😔"


def progress_bar(score: int, total: int, length: int = 10) -> str:
    filled = round(score / total * length) if total else 0
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


def result_message(score: int, total: int, quiz_title: str) -> str:
    percent = score_to_percent(score, total)
    emoji = result_emoji(percent)
    bar = progress_bar(score, total)

    if percent == 100:
        comment = "🎉 Mukammal natija! Barcha savollar to'g'ri!"
    elif percent >= 90:
        comment = "🌟 Ajoyib! Deyarli mukammal!"
    elif percent >= 70:
        comment = "👍 Yaxshi natija! Davom eting!"
    elif percent >= 50:
        comment = "📚 O'rtacha. Ko'proq o'qing!"
    else:
        comment = "😔 Qiyin bo'ldi. Qayta urinib ko'ring!"

    return (
        f"{'━' * 22}\n"
        f"{emoji} <b>Test yakunlandi!</b>\n"
        f"{'━' * 22}\n\n"
        f"📋 <b>{quiz_title}</b>\n\n"
        f"✅ To'g'ri javoblar: <b>{score}/{total}</b>\n"
        f"📊 Natija: <b>{percent}%</b>\n"
        f"📈 {bar}\n\n"
        f"💬 {comment}"
    )


def format_quiz_list(quizzes: list) -> str:
    if not quizzes:
        return (
            "📭 <b>Testlar topilmadi</b>\n\n"
            "➕ Yangi test yarating!"
        )
    lines = ["📋 <b>Barcha testlar:</b>\n"]
    for i, q in enumerate(quizzes, 1):
        lines.append(
            f"{i}. 📝 <b>{q['title']}</b>\n"
            f"   ❓ {q['question_count']} ta savol\n"
            f"   🕒 {str(q['created_at'])[:10]}\n"
        )
    return "\n".join(lines)


def achievement_check(score: int, total: int, total_games: int) -> str | None:
    percent = score_to_percent(score, total)
    if percent == 100 and total >= 5:
        return "🏆 Yangi yutuq: <b>Mukammal!</b> (5+ savolda 100%)"
    if total_games == 1:
        return "🎯 Yangi yutuq: <b>Birinchi qadam!</b>"
    if total_games == 10:
        return "🔥 Yangi yutuq: <b>10 ta o'yin!</b>"
    if total_games == 50:
        return "⚡ Yangi yutuq: <b>50 ta o'yin! Pro darajasi!</b>"
    return None


def question_card(
    q_index: int,
    total: int,
    question_text: str,
    options_list: list,
    time_left: int | None = None,
) -> str:
    options_text = "\n".join(
        f"  {chr(65 + i)}. {opt['text']}"
        for i, opt in enumerate(options_list)
    )
    time_str = f"\n⏱ <b>{time_left} sekund qoldi</b>" if time_left else ""
    return (
        f"{'━' * 22}\n"
        f"❓ <b>Savol {q_index + 1}/{total}</b>\n"
        f"{'━' * 22}\n\n"
        f"{question_text}\n\n"
        f"{options_text}"
        f"{time_str}"
    )
