from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


LICENSE_NAMES = {
    "car": "🚗 Авто",
    "truck": "🚛 Грузовик",
    "motorcycle": "🏍 Мотоцикл",
    "weapon": "🔫 Оружие",
    "fishing": "🎣 Рыбалка",
    "hunting": "🦌 Охота",
}


def licenses_menu() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"licenses:open:{license_id}")]
            for license_id, name in LICENSE_NAMES.items()]
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:page:2"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def license_action(license_id: str, can_pay: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if can_pay and license_id in {"car", "truck", "motorcycle", "weapon"}:
        rows.append([InlineKeyboardButton(text="📝 Начать экзамен", callback_data=f"licenses:exam:{license_id}")])
    elif can_pay:
        rows.append([InlineKeyboardButton(text="💳 Оплатить и получить", callback_data=f"licenses:buy:{license_id}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="licenses:menu"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def question(options: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=option, callback_data=f"licenses:answer:{index}")]
        for index, option in enumerate(options)
    ])
