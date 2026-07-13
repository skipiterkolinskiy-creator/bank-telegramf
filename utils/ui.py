from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from utils.database import Database


async def replace_menu(
    bot: Bot,
    database: Database,
    chat_id: int,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    user = database.get_user(user_id)
    old_message_id = user.get("last_menu_message_id") if user else None
    if old_message_id:
        try:
            await bot.delete_message(chat_id, old_message_id)
        except TelegramBadRequest:
            pass
    message = await bot.send_message(chat_id, text, reply_markup=reply_markup)
    if user:
        user["last_menu_message_id"] = message.message_id
        database.update_user(user_id, user)
    return message


async def answer_callback(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except TelegramBadRequest:
        pass
