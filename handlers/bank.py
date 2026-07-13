from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.bank import balance_menu, confirm_transfer, transfer_target
from keyboards.menu import back_main
from utils.bank_format import account_tail, masked_client, money, rub, transfer_debit_notice, transfer_income_notice
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()


class TransferState(StatesGroup):
    search = State()
    amount = State()


@router.callback_query(F.data == "bank:balance")
async def balance(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    user = database.upsert_user(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    text = (
        "🏦 <b>Мой счет</b>\n\n"
        f"Имя: <b>{user['name']}</b>\n"
        f"Баланс RUB: <b>{money(user['balances']['RUB'])} RUB</b>\n"
        f"USD: <b>{money(float(user['balances'].get('USD', 0.0)))}</b>\n"
        f"EUR: <b>{money(float(user['balances'].get('EUR', 0.0)))}</b>\n"
        f"Счет: <code>{account_tail(user)}</code>\n"
        f"Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"Username: @{user['username'] or 'нет'}\n"
        f"Z-ID: <code>{user['passport']}</code>"
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
        "💸 <b>Перевод денег</b>\n\nВведите Telegram ID, username, имя или Z-ID клиента.",
        back_main("bank:balance"),
    )


@router.message(TransferState.search)
async def transfer_search(message: Message, bot: Bot, database: Database, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    query = message.text
    matches = [user for user in database.find_users(query) if user["telegram_id"] != message.from_user.id]
    if not matches:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Клиент не найден. Попробуйте другой запрос.", back_main())
        return
    target = matches[0]
    is_private_zid = database.is_zid_query(query, target)
    await state.update_data(target_id=target["telegram_id"], private_zid=is_private_zid)
    if is_private_zid:
        text = (
            "🔍 <b>Получатель найден по Z-ID</b>\n\n"
            f"Получатель: <b>{masked_client(target)}</b>\n"
            f"Счет: <code>{account_tail(target)}</code>\n\n"
            "Имя и username скрыты для приватности перевода."
        )
    else:
        text = (
            "🔍 <b>Клиент найден</b>\n\n"
            f"Имя: <b>{target['name']}</b>\n"
            f"Username: @{target['username'] or 'нет'}\n"
            f"Z-ID: <code>{target['passport']}</code>\n"
            f"Счет: <code>{account_tail(target)}</code>"
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
    if data.get("private_zid"):
        receiver = masked_client(target)
    else:
        receiver = f"<b>{target['name']}</b>"
    text = f"Подтвердите перевод <b>{rub(amount)}</b> клиенту {receiver}."
    await replace_menu(bot, database, message.chat.id, message.from_user.id, text, confirm_transfer(target_id, amount))


@router.callback_query(F.data.startswith("bank:confirm:"))
async def transfer_confirm(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    _, _, target_id_raw, amount_raw = callback.data.split(":")
    target_id = int(target_id_raw)
    amount = float(amount_raw)
    sender_before = database.get_user(callback.from_user.id)
    receiver_before = database.get_user(target_id)
    ok = database.transfer(callback.from_user.id, target_id, amount)
    await state.clear()
    if ok:
        sender_after = database.get_user(callback.from_user.id)
        receiver_after = database.get_user(target_id)
        log_action(database, callback.from_user.id, "money_transfer", target_id=target_id, amount=amount)
        if receiver_after and sender_before:
            try:
                await bot.send_message(target_id, transfer_income_notice(sender_before, receiver_after, amount))
            except Exception as error:
                log_action(database, callback.from_user.id, "dm_transfer_notice_failed", target_id=target_id, error=str(error))
        if sender_after and receiver_after:
            try:
                await bot.send_message(callback.from_user.id, transfer_debit_notice(sender_after, receiver_after, amount))
            except Exception as error:
                log_action(database, callback.from_user.id, "dm_transfer_debit_notice_failed", target_id=callback.from_user.id, error=str(error))
        sender_balance = float(sender_after.get("balances", {}).get("RUB", 0.0)) if sender_after else 0.0
        receiver_text = masked_client(receiver_after or receiver_before or {}) if receiver_after or receiver_before else "клиент Z-Bank"
        text = (
            "✅ Перевод выполнен\n\n"
            f"Получатель: <b>{receiver_text}</b>\n"
            f"Сумма: <b>{rub(amount)}</b>\n"
            f"Ваш баланс: <b>{rub(sender_balance)}</b>"
        )
    else:
        text = "❌ Перевод не выполнен. Проверьте баланс и сумму."
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main())


@router.callback_query(F.data.in_({"bank:cancel", "bank:exchange"}))
async def bank_cancel(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    await state.clear()
    text = "Операция отменена." if callback.data == "bank:cancel" else "💱 Обмен валют будет подключен в следующем модуле."
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("bank:balance"))
