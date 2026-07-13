from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel() -> InlineKeyboardMarkup:
    items = [
        ("🔍 Поиск игрока", "admin:search"),
        ("✏️ Редактировать", "admin:search_edit"),
        ("💰 Выдать деньги", "admin:money_add"),
        ("💸 Снять деньги", "admin:money_remove"),
        ("📜 Лицензии", "admin:licenses"),
        ("🎒 Инвентарь", "admin:inventory"),
        ("⚖ Розыск", "admin:wanted"),
        ("💀 Жив / мертв", "admin:alive"),
        ("🚫 Бан", "admin:ban"),
        ("✅ Разбан", "admin:unban"),
        ("📋 Логи", "admin:logs"),
        ("📝 Заявки", "admin:applications"),
        ("⚙ Настройки", "admin:settings"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data)] for text, data in items
    ])


def player_card(player_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"admin:edit:{player_id}"),
            InlineKeyboardButton(text="💰 Деньги", callback_data=f"admin:money:{player_id}"),
        ],
        [
            InlineKeyboardButton(text="🎒 Инвентарь", callback_data=f"admin:inventory:{player_id}"),
            InlineKeyboardButton(text="📜 Лицензии", callback_data=f"admin:licenses:{player_id}"),
        ],
        [
            InlineKeyboardButton(text="⚖ Розыск", callback_data=f"admin:toggle_wanted:{player_id}"),
            InlineKeyboardButton(text="💀 Жив / мертв", callback_data=f"admin:toggle_alive:{player_id}"),
        ],
        [
            InlineKeyboardButton(text="🚫 Бан", callback_data=f"admin:ban:{player_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete:{player_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
    ])


def money_actions(player_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Выдать", callback_data=f"admin:money_add:{player_id}"),
            InlineKeyboardButton(text="💸 Снять", callback_data=f"admin:money_remove:{player_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:card:{player_id}")],
    ])
