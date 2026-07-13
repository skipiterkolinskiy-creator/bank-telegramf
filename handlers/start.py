from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.menu import main_menu
from utils.database import Database
from utils.ui import answer_callback, replace_menu


router = Router()


def main_text(name: str) -> str:
    return (
        f"🏦 <b>Z-Bank</b>\n\n"
        f"Добро пожаловать, <b>{name}</b>.\n"
        "Выберите нужный раздел."
    )


@router.message(CommandStart())
async def start(message: Message, bot: Bot, database: Database) -> None:
    user = message.from_user
    if not user:
        return
    profile = database.upsert_user(user.id, user.username, user.full_name)
    await replace_menu(bot, database, message.chat.id, user.id, main_text(profile["name"]), main_menu())


@router.callback_query(F.data.startswith("menu:page:"))
async def open_menu(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = callback.from_user
    profile = database.upsert_user(user.id, user.username, user.full_name)
    page = int(callback.data.split(":")[-1])
    await replace_menu(bot, database, callback.message.chat.id, user.id, main_text(profile["name"]), main_menu(page))


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await answer_callback(callback)
