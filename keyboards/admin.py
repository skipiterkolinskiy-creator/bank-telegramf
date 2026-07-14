from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel(is_mayor: bool = False) -> InlineKeyboardMarkup:
    if is_mayor:
        items = [
            ("🔍 Найти клиента", "admin:search"),
            ("📜 Лицензии", "admin:licenses"),
            ("⚠️ Проверка", "admin:wanted"),
            ("🔒 Заморозить", "admin:ban"),
            ("🔓 Разморозить", "admin:unban"),
            ("📋 Логи", "admin:logs"),
        ]
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data)] for text, data in items
        ])

    items = [
        ("🔍 Найти клиента", "admin:search"),
        ("✏️ Изменить клиента", "admin:search_edit"),
        ("💰 Пополнить баланс", "admin:money_add"),
        ("💸 Списать баланс", "admin:money_remove"),
        ("📜 Лицензии", "admin:licenses"),
        ("🎒 Инвентарь", "admin:inventory"),
        ("⚠️ Проверка", "admin:wanted"),
        ("✅ Активность", "admin:alive"),
        ("🔒 Заморозить", "admin:ban"),
        ("🔓 Разморозить", "admin:unban"),
        ("📋 Логи", "admin:logs"),
        ("📝 Обращения", "admin:applications"),
        ("⚙ Настройки", "admin:settings"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data)] for text, data in items
    ])


def player_card(player_id: int, is_mayor: bool = False, mayor_id: int | None = None) -> InlineKeyboardMarkup:
    if is_mayor:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📜 Лицензии", callback_data=f"admin:licenses:{player_id}")],
            [
                InlineKeyboardButton(text="⚠️ Проверка", callback_data=f"admin:toggle_wanted:{player_id}"),
                InlineKeyboardButton(text="🔒 Заморозить", callback_data=f"admin:ban:{player_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
        ])

    mayor_button_text = "🏛 Снять мэра" if mayor_id == player_id else "🏛 Назначить мэром"
    mayor_button_data = f"admin:mayor_remove:{player_id}" if mayor_id == player_id else f"admin:mayor_set:{player_id}"
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
            InlineKeyboardButton(text="⚠️ Проверка", callback_data=f"admin:toggle_wanted:{player_id}"),
            InlineKeyboardButton(text="✅ Активность", callback_data=f"admin:toggle_alive:{player_id}"),
        ],
        [
            InlineKeyboardButton(text="🔒 Заморозить", callback_data=f"admin:ban:{player_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:delete:{player_id}"),
        ],
        [InlineKeyboardButton(text=mayor_button_text, callback_data=mayor_button_data)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:panel")],
    ])


def money_actions(player_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Пополнить", callback_data=f"admin:money_add:{player_id}"),
            InlineKeyboardButton(text="💸 Списать", callback_data=f"admin:money_remove:{player_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:card:{player_id}")],
    ])


def license_manage(player_id: int, licenses: dict[str, str]) -> InlineKeyboardMarkup:
    rows = []
    for license_id, title in licenses.items():
        rows.append([InlineKeyboardButton(text=title, callback_data=f"admin:license_toggle:{player_id}:{license_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:card:{player_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
