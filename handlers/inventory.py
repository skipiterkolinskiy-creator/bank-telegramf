from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from utils.database import Database
from utils.ui import answer_callback, replace_menu


router = Router()


@router.callback_query(F.data.startswith("inventory:page:"))
async def inventory_page(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    page = int(callback.data.split(":")[-1])
    items = database.read("inventory").get(str(callback.from_user.id), [])
    per_page = 5
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    chunk = items[(page - 1) * per_page:page * per_page]
    lines = [f"{index}. {item.get('name', 'Предмет')} x{item.get('qty', 1)}" for index, item in enumerate(chunk, start=(page - 1) * per_page + 1)]
    text = "📦 <b>Инвентарь</b>\n\n" + ("\n".join(lines) if lines else "Пока пусто.")
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"inventory:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"inventory:page:{page + 1}"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:page:2"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
        ],
    ])
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, keyboard)
