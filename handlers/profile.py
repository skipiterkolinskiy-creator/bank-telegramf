from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from keyboards.menu import back_main
from utils.database import Database
from utils.ui import answer_callback, replace_menu


router = Router()


@router.callback_query(F.data.in_({"profile:menu", "profile:stats"}))
async def stats(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    stats_data = user["stats"]
    text = (
        "📈 <b>Статистика</b>\n\n"
        f"Всего переводов: <b>{stats_data.get('transfers', 0)}</b>\n"
        f"Получено: <b>{stats_data.get('received', 0.0):,.2f} RUB</b>\n"
        f"Потрачено: <b>{stats_data.get('spent', 0.0):,.2f} RUB</b>\n"
        f"Побед в казино: <b>{stats_data.get('casino_wins', 0)}</b>\n"
        f"Проигрышей в казино: <b>{stats_data.get('casino_losses', 0)}</b>\n"
        f"Донатов в казну: <b>{stats_data.get('donated', 0.0):,.2f} RUB</b>"
    ).replace(",", " ")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("menu:page:2"))


@router.callback_query(F.data == "profile:settings")
async def settings(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "⚙ Настройки профиля пока не требуют действий.", back_main("menu:page:2"))


@router.callback_query(F.data == "profile:help")
async def help_page(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "ℹ️ Управление идет через кнопки. Для админ-панели используйте /panel в STAFF GROUP.", back_main("menu:page:3"))
