from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from keyboards.menu import back_main
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()


class TreasuryState(StatesGroup):
    donate = State()


def treasury_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💝 Донат в казну", callback_data="treasury:donate")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="treasury:info")],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:page:1"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:page:1"),
        ],
    ])


@router.callback_query(F.data == "treasury:menu")
async def treasury_menu(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    treasury = database.read("treasury")
    mayor = database.get_user(treasury.get("mayor_id") or 0)
    text = (
        "🏛 <b>Государственная казна</b>\n\n"
        f"Баланс казны: <b>{treasury.get('balance', 0.0):,.2f} RUB</b>\n"
        f"Мэр: <b>{mayor['name'] if mayor else 'не назначен'}</b>"
    ).replace(",", " ")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, treasury_keyboard())


@router.callback_query(F.data == "treasury:donate")
async def donate_start(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    await state.set_state(TreasuryState.donate)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "Введите сумму доната в казну.", back_main("treasury:menu"))


@router.message(TreasuryState.donate)
async def donate_finish(message: Message, bot: Bot, database: Database, state: FSMContext) -> None:
    if not message.from_user or not message.text:
        return
    try:
        amount = round(float(message.text.replace(",", ".")), 2)
    except ValueError:
        await replace_menu(bot, database, message.chat.id, message.from_user.id, "Введите корректную сумму.", back_main("treasury:menu"))
        return
    ok = database.donate_to_treasury(message.from_user.id, amount, "donation")
    await state.clear()
    text = f"✅ В казну внесено <b>{amount:,.2f} RUB</b>.".replace(",", " ") if ok else "❌ Недостаточно средств."
    log_action(database, message.from_user.id, "treasury_donate", amount=amount, success=ok)
    await replace_menu(bot, database, message.chat.id, message.from_user.id, text, back_main("treasury:menu"))


@router.callback_query(F.data == "treasury:info")
async def treasury_info(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    await replace_menu(
        bot,
        database,
        callback.message.chat.id,
        callback.from_user.id,
        "ℹ️ Казна принимает донаты и комиссии. Все fee за лицензии автоматически поступают сюда.",
        back_main("treasury:menu"),
    )
