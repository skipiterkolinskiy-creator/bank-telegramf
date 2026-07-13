from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import Config
from keyboards.admin import admin_panel, money_actions, player_card
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()
STAFF_CHAT_ID = -5314530854


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
    return (
        "👤 <b>Карточка игрока</b>\n\n"
        f"Паспорт: <code>{player['passport']}</code>\n"
        f"Telegram ID: <code>{player['telegram_id']}</code>\n"
        f"Username: @{player.get('username') or 'нет'}\n"
        f"Имя: <b>{player['name']}</b>\n"
        f"Баланс: <b>{player['balances']['RUB']:,.2f} RUB</b>\n"
        f"Статус: {'забанен' if status.get('banned') else 'активен'}\n"
        f"Розыск: {'да' if status.get('wanted') else 'нет'}\n"
        f"Жив: {'да' if status.get('alive', True) else 'нет'}"
    ).replace(",", " ")


@router.message(F.text.startswith("/"))
async def panel(message: Message, bot: Bot, database: Database, config: Config) -> None:
    if not message.from_user:
        return
    if not is_panel_command(message.text):
        return
    if not is_staff_chat_id(message.chat.id, config):
        return
    database.upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await replace_menu(
        bot,
        database,
        message.chat.id,
        message.from_user.id,
        "⚙ <b>Админ-панель Z-Bank</b>\n\nДоступ открыт для этого staff-чата.",
        admin_panel(),
    )


@router.callback_query(F.data == "admin:panel")
async def panel_callback(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "⚙ <b>Админ-панель Z-Bank</b>\n\nДоступ открыт для этого staff-чата.",
        admin_panel(),
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
    await state.set_state(AdminState.search)
    await state.update_data(mode=callback.data)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "🔍 Введите Telegram ID, username, имя или паспорт игрока.",
        None,
    )


@router.message(AdminState.search)
async def admin_search(message: Message, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    if not message.from_user or not message.text or not is_staff_chat_id(message.chat.id, config):
        return
    data = await state.get_data()
    matches = database.find_users(message.text)
    if not matches:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Игрок не найден.", admin_panel())
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
            f"Введите сумму для игрока <b>{player['name']}</b>.",
            None,
        )
        return

    if mode in {"admin:ban", "admin:unban", "admin:wanted", "admin:alive"}:
        users = database.read("users")
        target = users[str(player["telegram_id"])]
        if mode == "admin:ban":
            target["status"]["banned"] = True
            action = "admin_ban"
        elif mode == "admin:unban":
            target["status"]["banned"] = False
            action = "admin_unban"
        elif mode == "admin:wanted":
            target["status"]["wanted"] = not target["status"].get("wanted", False)
            action = "admin_toggle_wanted"
        else:
            target["status"]["alive"] = not target["status"].get("alive", True)
            action = "admin_toggle_alive"
        users[str(player["telegram_id"])] = target
        database.write("users", users)
        log_action(database, message.from_user.id, action, target_id=player["telegram_id"])
        await state.clear()
        await replace_menu(bot, database, message.chat.id, message.from_user.id, player_text(target), player_card(player["telegram_id"]))
        return

    if mode == "admin:licenses":
        values = database.read("licenses").get(str(player["telegram_id"]), {})
        lines = [license_id for license_id, item in values.items() if item.get("active")]
        text = "📜 <b>Лицензии игрока</b>\n\n" + ("\n".join(lines) if lines else "Нет активных лицензий.")
        await state.clear()
        await replace_menu(bot, database, message.chat.id, message.from_user.id, text, player_card(player["telegram_id"]))
        return

    if mode == "admin:inventory":
        values = database.read("inventory").get(str(player["telegram_id"]), [])
        lines = [f"{item.get('name', 'Предмет')} x{item.get('qty', 1)}" for item in values]
        text = "🎒 <b>Инвентарь игрока</b>\n\n" + ("\n".join(lines) if lines else "Инвентарь пуст.")
        await state.clear()
        await replace_menu(bot, database, message.chat.id, message.from_user.id, text, player_card(player["telegram_id"]))
        return

    await state.clear()
    await replace_menu(bot, database, message.chat.id, message.from_user.id, player_text(player), player_card(player["telegram_id"]))


@router.message(AdminState.money_amount)
async def admin_money(message: Message, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    if not message.from_user or not message.text or not is_staff_chat_id(message.chat.id, config):
        return
    try:
        amount = round(float(message.text.replace(",", ".")), 2)
    except ValueError:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Введите корректную сумму.", admin_panel())
        return

    data = await state.get_data()
    target_id = int(data["target_id"])
    users = database.read("users")
    player = users.get(str(target_id))
    if not player or amount <= 0:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Операция невозможна.", admin_panel())
        return

    if data["operation"] == "admin:money_add":
        player["balances"]["RUB"] += amount
        action = "admin_give_money"
        result = f"✅ Выдано <b>{amount:,.2f} RUB</b> игроку <b>{player['name']}</b>."
    else:
        player["balances"]["RUB"] = max(0.0, player["balances"]["RUB"] - amount)
        action = "admin_remove_money"
        result = f"✅ Снято <b>{amount:,.2f} RUB</b> у игрока <b>{player['name']}</b>."

    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, message.from_user.id, action, target_id=target_id, amount=amount)
    await state.clear()
    await replace_menu(bot, database, message.chat.id, message.from_user.id, result.replace(",", " "), player_card(target_id))


@router.callback_query(F.data.startswith("admin:card:"))
async def open_player_card(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Игрок не найден.", admin_panel())
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), player_card(target_id))


@router.callback_query(F.data.startswith("admin:money:"))
async def money_menu(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Игрок не найден.", admin_panel())
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, f"💰 Деньги игрока <b>{player['name']}</b>", money_actions(target_id))


@router.callback_query(F.data.startswith("admin:money_add:") | F.data.startswith("admin:money_remove:"))
async def money_direct(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
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
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Игрок не найден.", admin_panel())
        return
    values = database.read("licenses").get(str(target_id), {})
    lines = [license_id for license_id, item in values.items() if item.get("active")]
    text = f"📜 <b>Лицензии игрока {player['name']}</b>\n\n" + ("\n".join(lines) if lines else "Нет активных лицензий.")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, player_card(target_id))


@router.callback_query(F.data.startswith("admin:inventory:"))
async def player_inventory(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    player = database.get_user(target_id)
    if not player:
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Игрок не найден.", admin_panel())
        return
    values = database.read("inventory").get(str(target_id), [])
    lines = [f"{item.get('name', 'Предмет')} x{item.get('qty', 1)}" for item in values]
    text = f"🎒 <b>Инвентарь игрока {player['name']}</b>\n\n" + ("\n".join(lines) if lines else "Инвентарь пуст.")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, player_card(target_id))


@router.callback_query(F.data.startswith("admin:toggle_wanted:"))
async def toggle_wanted(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["wanted"] = not player["status"].get("wanted", False)
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_toggle_wanted", target_id=target_id, value=player["status"]["wanted"])
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), player_card(target_id))


@router.callback_query(F.data.startswith("admin:toggle_alive:"))
async def toggle_alive(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["alive"] = not player["status"].get("alive", True)
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_toggle_alive", target_id=target_id, value=player["status"]["alive"])
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), player_card(target_id))


@router.callback_query(F.data.startswith("admin:ban:"))
async def ban_player(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    target_id = int(callback.data.split(":")[-1])
    users = database.read("users")
    player = users[str(target_id)]
    player["status"]["banned"] = True
    users[str(target_id)] = player
    database.write("users", users)
    log_action(database, callback.from_user.id, "admin_ban", target_id=target_id)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, player_text(player), player_card(target_id))


@router.callback_query(F.data == "admin:logs")
async def logs(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    recent = database.read("logs")[-10:]
    lines = [f"#{item['id']} {item['action']} actor={item.get('actor_id')}" for item in recent]
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "📋 <b>Логи</b>\n\n" + ("\n".join(lines) or "Пусто."), admin_panel())


@router.callback_query(F.data.startswith("admin:"))
async def admin_placeholder(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    if not callback.message or not is_staff_chat_id(callback.message.chat.id, config):
        return
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Раздел готов. Используйте поиск игрока или кнопки карточки.", admin_panel())
