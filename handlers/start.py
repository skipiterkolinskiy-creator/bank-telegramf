from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.menu import main_menu
from utils.bank_format import account_tail, money
from utils.database import Database
from utils.ui import answer_callback, replace_menu


router = Router()


def main_text(user: dict, is_new: bool = False) -> str:
    status = user.get("status", {})
    stats = user.get("stats", {})
    balances = user.get("balances", {})
    account_status = "заморожен" if status.get("banned") else "активен"
    access_status = "включен" if status.get("alive", True) else "выключен"
    intro = (
        "✅ <b>Z-ID выдан</b>\n"
        "Ваш банковский профиль создан.\n\n"
        if is_new
        else ""
    )
    return (
        f"{intro}"
        "🏦 <b>Z-Bank | Главное меню</b>\n\n"
        f"Клиент: <b>{user['name']}</b>\n"
        f"Z-ID: <code>{user['passport']}</code>\n"
        f"Счет: <code>{account_tail(user)}</code>\n"
        f"Баланс RUB: <b>{money(float(balances.get('RUB', 0.0)))} RUB</b>\n"
        f"USD: <b>{money(float(balances.get('USD', 0.0)))}</b>\n"
        f"EUR: <b>{money(float(balances.get('EUR', 0.0)))}</b>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{user.get('username') or 'нет'}\n\n"
        f"Аккаунт: <b>{account_status}</b>\n"
        f"Доступ: <b>{access_status}</b>\n"
        f"Переводов: <b>{stats.get('transfers', 0)}</b>\n\n"
        "Выберите действие ниже."
    )


@router.message(CommandStart())
async def start(message: Message, bot: Bot, database: Database) -> None:
    user = message.from_user
    if not user:
        return
    is_new = database.get_user(user.id) is None
    profile = database.upsert_user(user.id, user.username, user.full_name)
    await replace_menu(bot, database, message.chat.id, user.id, main_text(profile, is_new), main_menu())


@router.callback_query(F.data.startswith("menu:page:"))
async def open_menu(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = callback.from_user
    profile = database.upsert_user(user.id, user.username, user.full_name)
    page = int(callback.data.split(":")[-1])
    await replace_menu(bot, database, callback.message.chat.id, user.id, main_text(profile), main_menu(page))


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await answer_callback(callback)
