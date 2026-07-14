from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import Config
from keyboards.admin import admin_panel, license_manage, money_actions, player_card
from keyboards.licenses import LICENSE_NAMES
from utils.bank_format import merchant_credit_notice, merchant_debit_notice
from utils.database import Database
from utils.logger import log_action
from utils.permissions import can_open_staff_panel, is_admin, is_mayor
from utils.ui import answer_callback, replace_menu


router = Router()
STAFF_CHAT_ID = -1003993331647


class AdminState(StatesGroup):
    search = State()
    money_amount = State()


def is_staff_chat_id(chat_id: int, config: Config) -> bool:
    return chat_id == STAFF_CHAT_ID or chat_id == config.staff_group_id


def is_panel_command(text: str | None) -> bool:
    if not text:
        return False
    command = text.strip().split()[0].lower()
    command = command.split("@", 1)[0]
    return command in {"/panel", "/admin"}


def player_text(player: dict) -> str:
    status = player.get("status", {})
    roles = ", ".join(player.get("roles", [])) or "нет"
    return (
        "👤 <b>Карточка клиента</b>\n\n"
        f"Z-ID: <code>{player['passport']}</code>\n"
        f"Telegram ID: <code>{player['telegram_id']}</code>\n"
        f"Username: @{player.get('username') or 'нет'}\n"
        f"Имя: <b>{player['name']}</b>\n"
        f"Роли: <b>{roles}</b>\n"
        f"Баланс: <b>{player['balances']['RUB']:,.2f} RUB</b>\n"
        f"Аккаунт: {'заморожен' if status.get('banned') else 'активен'}\n"
        f"Проверка: {'требуется' if status.get('wanted') else 'нет'}\n"
        f"Доступ: {'включен' if status.get('alive', True) else 'выключен'}"
    ).replace(",", " ")


def panel_keyboard(database: Database, user_id: int):
    return admin_panel(is_mayor=is_mayor_id(database, user_id) and not is_admin_id(database, user_id))


def card_keyboard(database: Database, viewer_id: int, player_id: int):
    treasury = database.read("treasury")
    return player_card(
        player_id,
        is_mayor=is_mayor_id(database, viewer_id) and not is_admin_id(database, viewer_id),
        mayor_id=treasury.get("mayor_id"),
    )


def is_admin_id(database: Database, user_id: int) -> bool:
    admins = database.read("admins")
    profile = database.get_user(user_id)
    roles = [str(role).lower() for role in profile.get("roles", [])] if profile else []
    admin_ids = set(admins.get("owners", [])) | set(admins.get("admins", [])) | set(admins.get("ids", []))
    return user_id == 8548608434 or user_id in admin_ids or any("админ" in role or "admin" in role for role in roles)


def is_mayor_id(database: Database, user_id: int) -> bool:
    treasury = database.read("treasury")
    profile = database.get_user(user_id)
    roles = [str(role).lower() for role in profile.get("roles", [])] if profile else []
    return treasury.get("mayor_id") == user_id or "мэр" in roles or "mayor" in roles


def mayor_allowed_mode(mode: str | None) -> bool:
    return mode in {"admin:search", "admin:licenses", "admin:ban", "admin:unban", "admin:wanted"}


def license_status_titles(database: Database, target_id: int) -> dict[str, str]:
    active = database.read("licenses").get(str(target_id), {})
    titles = {}
    for license_id, name in LICENSE_NAMES.items():
        mark = "✅" if active.get(license_id, {}).get("active") else "➕"
        action = "забрать" if mark == "✅" else "выдать"
        titles[license_id] = f"{mark} {name} — {action}"
    return titles


@router.message(lambda message: is_panel_command(message.text))
async def panel(message: Message, bot: Bot, database: Database, config: Config) -> None:
    if not message.from_user:
        return
    if not is_staff_chat_id(message.chat.id, config):
        await message.answer(
            "⚙ Админ-панель работает только в staff-чате.\n"
            f"ID этого чата: <code>{message.chat.id}</code>\n"
            f"Нужный ID: <code>{STAFF_CHAT_ID}</code>"
        )
        return
    database.upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if not can_open_staff_panel(message.from_user, database):
        return
    mayor_mode = is_mayor(message.from_user, database) and not is_admin(message.from_user, database)
    title = "🏛 <b>Панель мэра Z-Bank</b>" if mayor_mode else "⚙ <b>Админ-панель Z-Bank</b>"
    subtitle = "Доступ мэра: поиск, лицензии, проверки и блокировки." if mayor_mode else "Доступ открыт для этого staff-чата."
    await replace_menu(
        bot,
        database,
        message.chat.id,
        message.from_user.id,
        f"{title}\n\n{subtitle}",
        admin_panel(is_mayor=mayor_mode),
    )


@router.callback_query(F.data == "admin:panel")
async def panel_callback(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    if not can_open_staff_panel(callback.from_user, database):
        return
    mayor_mode = is_mayor(callback.from_user, database) and not is_admin(callback.from_user, database)
    title = "🏛 <b>Панель мэра Z-Bank</b>" if mayor_mode else "⚙ <b>Админ-панель Z-Bank</b>"
    subtitle = "Доступ мэра: поиск, лицензии, проверки и блокировки." if mayor_mode else "Доступ открыт для этого staff-чата."
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        f"{title}\n\n{subtitle}",
        admin_panel(is_mayor=mayor_mode),
    )


@router.callback_query(F.data.in_({
    "admin:search",
    "admin:search_edit",
    "admin:money_add",
    "admin:money_remove",
    "admin:unban",
    "admin:ban",
    "admin:wanted",
    "admin:alive",
    "admin:licenses",
    "admin:inventory",
}))
async def admin_search_start(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    if is_mayor(callback.from_user, database) and not is_admin(callback.from_user, database) and not mayor_allowed_mode(callback.data):
        await replace_menu(
            bot,
            database,
            callback.message.chat.id,
            callback.from_user.id,
            "🏛 Доступ мэра ограничен поиском, лицензиями, проверками и блокировками.",
            admin_panel(is_mayor=True),
        )
        return
    await state.set_state(AdminState.search)
    await state.update_data(mode=callback.data)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "🔍 Введите Telegram ID, username, имя или Z-ID клиента.",
        None,
    )


@router.message(AdminState.search)
async def admin_search(message: Message, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    if not message.from_user or not message.text or not is_staff_chat_id(message.chat.id, config):
        return
    if not can_open_staff_panel(message.from_user, database):
        return
    data = await state.get_data()
    matches = database.find_users(message.text)
    if not matches:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Клиент не найден.", panel_keyboard(database, message.from_user.id))
        return

    player = matches[0]
    mode = data.get("mode")

    if mode in {"admin:money_add", "admin:money_remove"}:
        await state.set_state(AdminState.money_amount)
        await state.update_data(target_id=player["telegram_id"], operation=mode)
        await replace_menu(
            bot,
            database,
            message.chat.id,
            message.from_user.id,
            f"Введите сумму для клиента <b>{player['name']}</b>.",
            None,
        )
        return

    if mode in {"admin:ban", "admin:unban", "admin:wanted", "admin:alive"}:
        users = database.read("users")
        target = users[str(player["telegram_id"])]
        if mode == "admin:ban":
            target["status"]["banned"] = True
            action = "admin_freeze_account"
        elif mode == "admin:unban":
            target["status"]["banned"] = False
            action = "admin_unfreeze_account"
        elif mode == "admin:wanted":
            target["status"]["wanted"] = not target["status"].get("wanted", False)
            action = "admin_toggle_review"
        else:
            target["status"]["alive"] = not target["status"].get("alive", True)
            action = "admin_toggle_access"
        users[str(player["telegram_id"])] = target
        database.write("users", users)
        log_action(database, message.from_user.id, action, target_id=player["telegram_id"])
        await state.clear()
        await replace_menu(bot, database, message.chat.id, message.from_user.id, player_text(target), card_keyboard(database, message.from_user.id, player["telegram_id"]))
        return

    if mode == "admin:licenses":
        values = database.read("licenses").get(str(player["telegram_id"]), {})
        lines = [license_id for license_id, item in values.items() if item.get("active")]
        text = "📜 <b>Лицензии клиента</b>\n\n" + ("\n".join(lines) if lines else "Нет активных лицензий.")
        await state.clear()
        await replace_menu(
            bot,
            database,
            message.chat.id,
            message.from_user.id,
            text,
            license_manage(player["telegram_id"], license_status_titles(database, player["telegram_id"])),
        )
        return

    if mode == "admin:inventory":
        values = database.read("inventory").get(str(player["telegram_id"]), [])
        lines = [f"{item.get('name', 'Предмет')} x{item.get('qty', 1)}" for item in values]
        text = "🎒 <b>Инвентарь клиента</b>\n\n" + ("\n".join(lines) if lines else "Инвентарь пуст.")
        await state.clear()
        await replace_menu(bot, database, message.chat.id, message.from_user.id, text, card_keyboard(database, message.from_user.id, player["telegram_id"]))
        return

    await state.clear()
    await replace_menu(bot, database, message.chat.id, message.from_user.id, player_text(player), card_keyboard(database, message.from_user.id, player["telegram_id"]))


@router.message(AdminState.money_amount)
async def admin_money(message: Message, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    if not message.from_user or not message.text or not is_staff_chat_id(message.chat.id, config):
        return
    if not is_admin(message.from_user, database):
        return
    try:
        amount = round(float(message.text.replace(",", ".")), 2)
    except ValueError:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Введите корректную сумму.", panel_keyboard(database, message.from_user.id))
        return

    data = await state.get_data()
    target_id = int(data["target_id"])
    users = database.read("users")
    player = users.get(str(target_id))
    if not player or amount <= 0:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Операция невозможна.", panel_keyboard(database, message.from_user.id))
        return

    if data["operation"] == "admin:money_add":
        player["balances"]["RUB"] += amount
        action = "admin_give_money"
        result = f"✅ Баланс пополнен на <b>{amount:,.2f} RUB</b>. Клиент: <b>{player['name']}</b>."
        notice_text = merchant_credit_notice(player, "Z-Bank", amount)
    else:
        player["balances"]["RUB"] = max(0.0, player["balances"]["RUB"] - amount)
        action = "admin_remove_money"
        result = f"✅ С баланса списано <b>{amount:,.2f} RUB</b>. Клиент: <b>{player['name']}</b>."
        notice_text = merchant_debit_notice(player, "Z-Bank", amount)

    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, message.from_user.id, action, target_id=target_id, amount=amount)
    try:
        await bot.send_message(target_id, notice_text)
    except Exception as error:
        log_action(database, message.from_user.id, "dm_admin_money_notice_failed", target_id=target_id, error=str(error))
    await state.clear()
    await replace_menu(bot, database, message.chat.id, message.from_user.id, result.replace(",", " "), card_keyboard(database, message.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:card:"))
async def open_player_card(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), card_keyboard(database, callback.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:money:"))
async def money_menu(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, f"💰 Баланс клиента <b>{player['name']}</b>", money_actions(target_id))


@router.callback_query(F.data.startswith("admin:money_add:") | F.data.startswith("admin:money_remove:"))
async def money_direct(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return
    parts = callback.data.split(":")
    operation = "admin:money_add" if parts[1] == "money_add" else "admin:money_remove"
    target_id = int(parts[-1])
    await state.set_state(AdminState.money_amount)
    await state.update_data(target_id=target_id, operation=operation)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Введите сумму.", None)


@router.callback_query(F.data.startswith("admin:licenses:"))
async def player_licenses(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return
    values = database.read("licenses").get(str(target_id), {})
    lines = [license_id for license_id, item in values.items() if item.get("active")]
    text = f"📜 <b>Лицензии клиента {player['name']}</b>\n\n" + ("\n".join(lines) if lines else "Нет активных лицензий.")
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        text,
        license_manage(target_id, license_status_titles(database, target_id)),
    )


@router.callback_query(F.data.startswith("admin:license_toggle:"))
async def toggle_license(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return

    _, _, target_raw, license_id = callback.data.split(":", 3)
    target_id = int(target_raw)
    player = database.get_user(target_id)
    if not player or license_id not in LICENSE_NAMES:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент или лицензия не найдены.", panel_keyboard(database, callback.from_user.id))
        return

    licenses = database.read("licenses")
    user_licenses = licenses.setdefault(str(target_id), {})
    current = user_licenses.get(license_id, {}).get("active", False)
    if current:
        user_licenses[license_id] = {"active": False, "revoked_at": database.now(), "revoked_by": callback.from_user.id}
        action = "admin_license_revoked"
        result = "забрана"
    else:
        user_licenses[license_id] = {"active": True, "issued_at": database.now(), "issued_by": callback.from_user.id}
        action = "admin_license_issued"
        result = "выдана"
    licenses[str(target_id)] = user_licenses
    database.write("licenses", licenses)
    log_action(database, callback.from_user.id, action, target_id=target_id, license=license_id)

    values = database.read("licenses").get(str(target_id), {})
    lines = [item_id for item_id, item in values.items() if item.get("active")]
    text = (
        f"📜 <b>Лицензии клиента {player['name']}</b>\n\n"
        f"Лицензия {LICENSE_NAMES[license_id]} {result}.\n\n"
        + ("\n".join(lines) if lines else "Нет активных лицензий.")
    )
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        text,
        license_manage(target_id, license_status_titles(database, target_id)),
    )


@router.callback_query(F.data.startswith("admin:inventory:"))
async def player_inventory(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return
    values = database.read("inventory").get(str(target_id), [])
    lines = [f"{item.get('name', 'Предмет')} x{item.get('qty', 1)}" for item in values]
    text = f"🎒 <b>Инвентарь клиента {player['name']}</b>\n\n" + ("\n".join(lines) if lines else "Инвентарь пуст.")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, card_keyboard(database, callback.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:toggle_wanted:"))
async def toggle_wanted(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["wanted"] = not player["status"].get("wanted", False)
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_toggle_review", target_id=target_id, value=player["status"]["wanted"])
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), card_keyboard(database, callback.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:toggle_alive:"))
async def toggle_alive(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["alive"] = not player["status"].get("alive", True)
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_toggle_access", target_id=target_id, value=player["status"]["alive"])
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), card_keyboard(database, callback.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:ban:"))
async def ban_player(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["banned"] = True
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_freeze_account", target_id=target_id)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), card_keyboard(database, callback.from_user.id, target_id))


@router.callback_query(F.data.startswith("admin:mayor_set:"))
async def set_mayor(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return

    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users.get(str(target_id))
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return

    treasury = database.read("treasury")
    previous_id = treasury.get("mayor_id")
    if previous_id and str(previous_id) in users:
        previous = users[str(previous_id)]
        previous["roles"] = [role for role in previous.get("roles", []) if str(role).lower() not in {"мэр", "mayor"}]
        users[str(previous_id)] = previous

    roles = [role for role in player.get("roles", []) if str(role).lower() not in {"мэр", "mayor"}]
    roles.append("мэр")
    player["roles"] = roles
    users[str(target_id)] = player
    treasury["mayor_id"] = target_id

    database.write("users", users)
    database.write("treasury", treasury)
    log_action(database, callback.from_user.id, "mayor_assigned", target_id=target_id, previous_id=previous_id)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        f"🏛 <b>{player['name']}</b> назначен мэром. Теперь ему доступна панель мэра в staff-чате.",
        card_keyboard(database, callback.from_user.id, target_id),
    )


@router.callback_query(F.data.startswith("admin:mayor_remove:"))
async def remove_mayor(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not is_admin(callback.from_user, database):
        return

    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users.get(str(target_id))
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Клиент не найден.", panel_keyboard(database, callback.from_user.id))
        return

    player["roles"] = [role for role in player.get("roles", []) if str(role).lower() not in {"мэр", "mayor"}]
    users[str(target_id)] = player
    treasury = database.read("treasury")
    if treasury.get("mayor_id") == target_id:
        treasury["mayor_id"] = None

    database.write("users", users)
    database.write("treasury", treasury)
    log_action(database, callback.from_user.id, "mayor_removed", target_id=target_id)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        f"🏛 <b>{player['name']}</b> больше не мэр.",
        card_keyboard(database, callback.from_user.id, target_id),
    )


@router.callback_query(F.data == "admin:logs")
async def logs(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    recent = database.read("logs")[-10:]
    lines = [f"#{item['id']} {item['action']} actor={item.get('actor_id')}" for item in recent]
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "📋 <b>Логи</b>\n\n" + ("\n".join(lines) or "Пусто."), panel_keyboard(database, callback.from_user.id))


@router.callback_query(F.data.startswith("admin:"))
async def admin_placeholder(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    if not can_open_staff_panel(callback.from_user, database):
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Раздел готов. Используйте поиск клиента или кнопки карточки.", panel_keyboard(database, callback.from_user.id))
