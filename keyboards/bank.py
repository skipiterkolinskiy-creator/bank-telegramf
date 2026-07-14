from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def balance_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Перевести", callback_data="bank:transfer"),
            InlineKeyboardButton(text="💱 Обмен", callback_data="bank:exchange"),
        ],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="profile:stats")],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:page:1"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
        ],
    ])


def transfer_target(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выбрать клиента", callback_data=f"bank:transfer_target:{target_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="bank:cancel")],
    ])


def confirm_transfer(target_id: int, amount: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"bank:confirm:{target_id}:{amount}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="bank:cancel"),
        ]
    ])
