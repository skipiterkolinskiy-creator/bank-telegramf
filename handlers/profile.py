from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from keyboards.menu import back_main
from utils.database import Database
from utils.ui import answer_callback, replace_menu


router = Router()


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


@router.callback_query(F.data == "profile:menu")
async def profile_card(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    balances = user["balances"]
    status = user["status"]
    text = (
        "👤 <b>Карточка клиента</b>\n\n"
        f"Имя: <b>{user['name']}</b>\n"
        f"Z-ID: <code>{user['passport']}</code>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{user.get('username') or 'нет'}\n\n"
        f"Баланс RUB: <b>{money(float(balances.get('RUB', 0.0)))} RUB</b>\n"
        f"USD: <b>{money(float(balances.get('USD', 0.0)))}</b>\n"
        f"EUR: <b>{money(float(balances.get('EUR', 0.0)))}</b>\n\n"
        f"Аккаунт: <b>{'заморожен' if status.get('banned') else 'активен'}</b>\n"
        f"Доступ: <b>{'включен' if status.get('alive', True) else 'выключен'}</b>"
    )
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("menu:page:3"))


@router.callback_query(F.data == "profile:stats")
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
