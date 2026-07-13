from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(page: int = 1) -> InlineKeyboardMarkup:
    pages = {
        1: [
            ("🏦 Баланс", "bank:balance"),
            ("💸 Перевод", "bank:transfer"),
            ("🏛 Казна", "treasury:menu"),
            ("🎰 Казино", "casino:menu"),
        ],
        2: [
            ("📜 Лицензии", "licenses:menu"),
            ("📦 Инвентарь", "inventory:page:1"),
            ("📈 Статистика", "profile:stats"),
            ("⚙ Настройки", "profile:settings"),
        ],
        3: [
            ("👤 Профиль", "profile:menu"),
            ("ℹ️ Помощь", "profile:help"),
        ],
    }
    rows = [[InlineKeyboardButton(text=text, callback_data=data)] for text, data in pages.get(page, pages[1])]
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"menu:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page}/3", callback_data="noop"))
    if page < 3:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"menu:page:{page + 1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_main(back_to: str = "menu:page:1") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
        ]
    ])
