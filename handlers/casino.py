from __future__ import annotations

import random

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.menu import back_main
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()


class CasinoState(StatesGroup):
    bet = State()


@router.callback_query(F.data == "casino:menu")
async def casino_menu(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    await state.set_state(CasinoState.bet)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "🎰 <b>Казино</b>\n\nИгра в кости. Введите ставку в RUB.",
        back_main(),
    )


@router.message(CasinoState.bet)
async def casino_bet(message: Message, bot: Bot, database: Database, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    try:
        bet = round(float(message.text.replace(",", ".")), 2)
    except ValueError:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Введите корректную ставку.", back_main())
        return
    user = database.get_user(message.from_user.id)
    if not user or bet <= 0 or user["balances"]["RUB"] < bet:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "❌ Ставка невозможна.", back_main())
        return
    roll = random.randint(1, 6)
    won = roll >= 4
    users = database.read("users")
    profile = users[str(message.from_user.id)]
    casino = database.read("casino")
    if won:
        profit = bet
        profile["balances"]["RUB"] += profit
        profile["stats"]["casino_wins"] += 1
        text = f"🎲 Выпало <b>{roll}</b>\n\n✅ Победа! Вы выиграли <b>{profit:,.2f} RUB</b>."
    else:
        profile["balances"]["RUB"] -= bet
        profile["stats"]["casino_losses"] += 1
        text = f"🎲 Выпало <b>{roll}</b>\n\n❌ Проигрыш. Ставка <b>{bet:,.2f} RUB</b> списана."
    users[str(message.from_user.id)] = profile
    casino.setdefault("games", []).append({
        "telegram_id": message.from_user.id,
        "bet": bet,
        "roll": roll,
        "won": won,
        "created_at": database.now(),
    })
    database.write("users", users)
    database.write("casino", casino)
    log_action(database, message.from_user.id, "casino_game", bet=bet, roll=roll, won=won)
    await state.clear()
    await replace_menu(bot, database, message.chat.id, message.from_user.id, text.replace(",", " "), back_main())
