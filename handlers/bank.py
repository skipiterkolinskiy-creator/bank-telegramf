from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.bank import balance_menu, confirm_transfer, transfer_target
from keyboards.menu import back_main
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()


class TransferState(StatesGroup):
    search = State()
    amount = State()


def money(value: float) -> str:
    return f"{value:,.2f}".replace(",", " ")


@router.callback_query(F.data == "bank:balance")
async def balance(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    text = (
        "🏦 <b>Баланс</b>\n\n"
        f"Имя: <b>{user['name']}</b>\n"
        f"Баланс: <b>{money(user['balances']['RUB'])} RUB</b>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{user['username'] or 'нет'}\n"
        f"Паспорт: <code>{user['passport']}</code>"
    )
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, balance_menu())


@router.callback_query(F.data == "bank:transfer")
async def transfer_start(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    await state.set_state(TransferState.search)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "💸 <b>Перевод денег</b>\n\nВведите Telegram ID, username, ник или паспорт игрока.",
        back_main("bank:balance"),
    )


@router.message(TransferState.search)
async def transfer_search(message: Message, bot: Bot, database: Database, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    matches = [user for user in database.find_users(message.text) if user["telegram_id"] != message.from_user.id]
    if not matches:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Игрок не найден. Попробуйте другой запрос.", back_main())
        return
    target = matches[0]
    await state.update_data(target_id=target["telegram_id"])
    text = (
        "🔍 <b>Найден игрок</b>\n\n"
        f"Имя: <b>{target['name']}</b>\n"
        f"Username: @{target['username'] or 'нет'}\n"
        f"Паспорт: <code>{target['passport']}</code>"
    )
    await replace_menu(bot, database, message.chat.id, message.from_user.id, text, transfer_target(target["telegram_id"]))


@router.callback_query(F.data.startswith("bank:transfer_target:"))
async def transfer_amount(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    target_id = int(callback.data.split(":")[-1])
    await state.update_data(target_id=target_id)
    await state.set_state(TransferState.amount)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Введите сумму перевода в RUB.", back_main())


@router.message(TransferState.amount)
async def transfer_amount_entered(message: Message, bot: Bot, database: Database, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    try:
        amount = round(float(message.text.replace(",", ".")), 2)
    except ValueError:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Введите корректную сумму.", back_main())
        return
    data = await state.get_data()
    target_id = int(data["target_id"])
    target = database.get_user(target_id)
    if not target or amount <= 0:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Перевод невозможен.", back_main())
        return
    text = f"Подтвердите перевод <b>{money(amount)} RUB</b> игроку <b>{target['name']}</b>."
    await replace_menu(bot, database, message.chat.id, message.from_user.id, text, confirm_transfer(target_id, amount))


@router.callback_query(F.data.startswith("bank:confirm:"))
async def transfer_confirm(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    _, _, target_id_raw, amount_raw = callback.data.split(":")
    amount = float(amount_raw)
    ok = database.transfer(callback.from_user.id, int(target_id_raw), amount)
    await state.clear()
    if ok:
        log_action(database, callback.from_user.id, "money_transfer", target_id=int(target_id_raw), amount=amount)
        text = f"✅ Перевод выполнен.\nСумма: <b>{money(amount)} RUB</b>"
    else:
        text = "❌ Перевод не выполнен. Проверьте баланс и сумму."
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main())


@router.callback_query(F.data.in_({"bank:cancel", "bank:exchange"}))
async def bank_cancel(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    await state.clear()
    text = "Операция отменена." if callback.data == "bank:cancel" else "💱 Обмен валют будет подключен в следующем модуле."
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("bank:balance"))
