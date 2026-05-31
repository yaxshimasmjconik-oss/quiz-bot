"""
Admin panel:
- Statistika
- Foydalanuvchilar ro'yxati
- Barcha testlar
- Hammaga xabar yuborish
"""
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import queries
from utils.helpers import is_admin

router = Router()


class BroadcastSG(StatesGroup):
    waiting_message = State()


def admin_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="ap_stats")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="ap_users")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Barcha testlar", callback_data="ap_quizzes")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="ap_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="main_menu")
    )
    return builder.as_markup()


def back_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_panel")
    )
    return builder.as_markup()


# ── ADMIN PANEL ────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("❗ Siz admin emassiz!")
        return
    await message.answer(
        "🔐 <b>Admin Panel</b>\n\nNima qilmoqchisiz?",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Siz admin emassiz!", show_alert=True)
        return
    await callback.message.edit_text(
        "🔐 <b>Admin Panel</b>\n\nNima qilmoqchisiz?",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()


# ── STATISTIKA ─────────────────────────────────────────────

@router.callback_query(F.data == "ap_stats")
async def cb_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    stats = await queries.get_stats()
    await callback.message.edit_text(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"📝 Testlar: <b>{stats['quizzes']}</b>\n"
        f"✅ Yakunlangan urinishlar: <b>{stats['attempts']}</b>",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


# ── FOYDALANUVCHILAR ───────────────────────────────────────

@router.callback_query(F.data == "ap_users")
async def cb_users(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    users = await queries.get_all_users()
    if not users:
        await callback.message.edit_text(
            "👥 Hali foydalanuvchilar yo'q.",
            reply_markup=back_admin_kb(),
        )
        await callback.answer()
        return

    lines = [f"👥 <b>Foydalanuvchilar ({len(users)} ta):</b>\n"]
    for i, u in enumerate(users[:30], 1):
        name = u["full_name"] or "Nomsiz"
        username = f"@{u['username']}" if u["username"] else "—"
        lines.append(f"{i}. {name} {username}")

    if len(users) > 30:
        lines.append(f"\n<i>... va yana {len(users) - 30} ta</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


# ── BARCHA TESTLAR ─────────────────────────────────────────

@router.callback_query(F.data == "ap_quizzes")
async def cb_all_quizzes(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    quizzes = await queries.get_all_quizzes()
    if not quizzes:
        await callback.message.edit_text(
            "📋 Hali testlar yo'q.",
            reply_markup=back_admin_kb(),
        )
        await callback.answer()
        return

    lines = [f"📋 <b>Barcha testlar ({len(quizzes)} ta):</b>\n"]
    for i, q in enumerate(quizzes, 1):
        lines.append(
            f"{i}. <b>{q['title']}</b>\n"
            f"   ❓ {q['question_count']} savol | "
            f"🕒 {str(q['created_at'])[:10]}"
        )

    builder = InlineKeyboardBuilder()
    for q in quizzes:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {q['title'][:30]}",
                callback_data=f"ap_del_{q['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_panel")
    )

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ap_del_"))
async def cb_ap_delete(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    quiz_id = int(callback.data.split("_")[2])
    quiz = await queries.get_quiz(quiz_id)
    if not quiz:
        await callback.answer("Test topilmadi!", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Ha, o'chir",
            callback_data=f"ap_confirm_{quiz_id}",
        ),
        InlineKeyboardButton(
            text="❌ Yo'q",
            callback_data="ap_quizzes",
        ),
    )
    await callback.message.edit_text(
        f"⚠️ <b>{quiz['title']}</b> testini o'chirasizmi?",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ap_confirm_"))
async def cb_ap_confirm_delete(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    quiz_id = int(callback.data.split("_")[2])
    await queries.delete_quiz(quiz_id)
    await callback.answer("✅ O'chirildi!", show_alert=True)

    quizzes = await queries.get_all_quizzes()
    if not quizzes:
        await callback.message.edit_text(
            "📋 Testlar yo'q.",
            reply_markup=back_admin_kb(),
        )
        return

    lines = [f"📋 <b>Barcha testlar ({len(quizzes)} ta):</b>\n"]
    for i, q in enumerate(quizzes, 1):
        lines.append(
            f"{i}. <b>{q['title']}</b>\n"
            f"   ❓ {q['question_count']} savol"
        )

    builder = InlineKeyboardBuilder()
    for q in quizzes:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {q['title'][:30]}",
                callback_data=f"ap_del_{q['id']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="◀️ Admin panel", callback_data="admin_panel")
    )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup(),
    )


# ── XABAR YUBORISH ─────────────────────────────────────────

@router.callback_query(F.data == "ap_broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("❗ Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(BroadcastSG.waiting_message)
    await callback.message.edit_text(
        "📢 <b>Hammaga xabar yuborish</b>\n\n"
        "Xabar matnini yozing:\n"
        "<i>(Bekor qilish uchun /cancel)</i>",
        reply_markup=back_admin_kb(),
    )
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(BroadcastSG.waiting_message)
async def msg_broadcast(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    user_ids = await queries.get_all_user_ids()

    sent = 0
    failed = 0
    status_msg = await message.answer(
        f"📢 Yuborilmoqda... 0/{len(user_ids)}"
    )

    for user_id in user_ids:
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Admin xabari:</b>\n\n{message.text}",
            )
            sent += 1
        except Exception:
            failed += 1

        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(
                    f"📢 Yuborilmoqda... {sent + failed}/{len(user_ids)}"
                )
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborildi!</b>\n\n"
        f"✅ Muvaffaqiyatli: {sent}\n"
        f"❌ Yuborilmadi: {failed}",
        reply_markup=back_admin_kb(),
    )
