from __future__ import annotations

import random
from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import Config
from keyboards.licenses import LICENSE_NAMES, license_action, licenses_menu, question
from keyboards.menu import back_main
from utils.database import Database
from utils.logger import log_action
from utils.ui import answer_callback, replace_menu


router = Router()


Question = dict[str, Any]


CAR_TRUCK_EXAM: list[Question] = [
    {"q": "Что означает красный сигнал светофора?", "a": "Движение запрещено", "o": ["Можно ехать", "Только направо", "Уступить"]},
    {"q": "Когда водитель обязан пристегнуться?", "a": "Перед началом движения", "o": ["После разгона", "Только на трассе", "Только ночью"]},
    {"q": "Что нужно сделать перед перестроением?", "a": "Включить поворотник и убедиться в безопасности", "o": ["Посигналить", "Резко ускориться", "Остановиться"]},
    {"q": "Главное правило на пешеходном переходе?", "a": "Уступить пешеходам", "o": ["Ускориться", "Подать сигнал", "Ехать без остановки"]},
    {"q": "Что означает знак STOP?", "a": "Остановка обязательна", "o": ["Остановка запрещена", "Парковка", "Главная дорога"]},
    {"q": "Можно ли управлять после алкоголя?", "a": "Нельзя", "o": ["Можно медленно", "Можно по двору", "Можно с аварийкой"]},
    {"q": "Дистанция нужна для чего?", "a": "Для безопасного торможения", "o": ["Для красоты", "Для обгона", "Для сигнала"]},
    {"q": "Кто имеет преимущество на круге?", "a": "Тот, кто уже движется по кругу", "o": ["Въезжающий", "Самый быстрый", "Грузовик"]},
    {"q": "Что делать при ДТП?", "a": "Остановиться и вызвать службы", "o": ["Уехать", "Скрыть следы", "Продолжить путь"]},
    {"q": "Когда включаются фары?", "a": "В темноте и при плохой видимости", "o": ["Только зимой", "Только в городе", "Никогда"]},
    {"q": "Что запрещено на перекрестке?", "a": "Выезжать при заторе за перекрестком", "o": ["Смотреть в зеркала", "Снижать скорость", "Уступать"]},
    {"q": "Что означает сплошная линия?", "a": "Пересекать запрещено", "o": ["Можно обгонять", "Парковка", "Велодорожка"]},
    {"q": "Что проверяют перед поездкой?", "a": "Тормоза, свет, состояние авто", "o": ["Цвет машины", "Музыку", "Номер телефона"]},
    {"q": "Разрешен ли телефон за рулем?", "a": "Только с hands-free", "o": ["Всегда", "На перекрестке", "При обгоне"]},
    {"q": "Что делать при спецсигнале?", "a": "Уступить дорогу", "o": ["Обогнать", "Ехать рядом", "Заблокировать"]},
]

MOTORCYCLE_EXAM = CAR_TRUCK_EXAM[:10] + [
    {"q": "Что обязательно для мотоциклиста?", "a": "Шлем", "o": ["Кепка", "Наушники", "Темные очки"]},
    {"q": "Как безопасно проходить поворот?", "a": "Снизить скорость заранее", "o": ["Тормозить в наклоне", "Закрыть глаза", "Резко газовать"]},
    {"q": "Почему важна защитная экипировка?", "a": "Снижает риск травм", "o": ["Увеличивает штраф", "Мешает управлять", "Не нужна"]},
    {"q": "Можно ли ехать между рядами опасно быстро?", "a": "Нельзя", "o": ["Можно всегда", "Можно без шлема", "Нужно"]},
    {"q": "Что особенно важно на мокрой дороге?", "a": "Плавные действия", "o": ["Резкие маневры", "Максимальная скорость", "Езда без света"]},
]

WEAPON_EXAM = CAR_TRUCK_EXAM[:8] + [
    {"q": "Главное правило обращения с оружием?", "a": "Считать оружие заряженным", "o": ["Направлять на людей", "Играть", "Хранить открыто"]},
    {"q": "Где хранить оружие?", "a": "В безопасном закрытом месте", "o": ["На столе", "В машине", "У друга"]},
    {"q": "Можно ли передавать оружие без разрешения?", "a": "Нельзя", "o": ["Можно всем", "Можно за деньги", "Можно ночью"]},
    {"q": "Когда применять оружие?", "a": "Только по закону и при угрозе", "o": ["Для спора", "Для шутки", "Для демонстрации"]},
    {"q": "Что делать перед чисткой?", "a": "Проверить, что оружие разряжено", "o": ["Нажать на спуск", "Зарядить", "Отдать ребенку"]},
    {"q": "Что запрещено владельцу?", "a": "Носить оружие в состоянии опьянения", "o": ["Хранить документы", "Проверять сейф", "Учиться безопасности"]},
    {"q": "Что делать при потере оружия?", "a": "Немедленно сообщить", "o": ["Молчать", "Купить новое", "Списать"]},
    {"q": "Документы на оружие нужны?", "a": "Да, всегда", "o": ["Нет", "Только на фото", "Только друзьям"]},
]


def exam_pool(license_id: str) -> tuple[list[Question], int, int]:
    if license_id in {"car", "truck"}:
        return CAR_TRUCK_EXAM, 15, 13
    if license_id == "motorcycle":
        return MOTORCYCLE_EXAM, 15, 13
    return WEAPON_EXAM, 16, 14


@router.callback_query(F.data == "licenses:menu")
async def menu(callback: CallbackQuery, bot: Bot, database: Database) -> None:
    await answer_callback(callback)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "📜 <b>Лицензии</b>\n\nВыберите категорию.", licenses_menu())


@router.callback_query(F.data.startswith("licenses:open:"))
async def open_license(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    license_id = callback.data.split(":")[-1]
    owned = database.has_license(callback.from_user.id, license_id)
    price = config.license_prices.get(license_id, 0.0) if config.license_prices else 0.0
    extra = ""
    if license_id == "hunting" and not database.has_license(callback.from_user.id, "weapon"):
        extra = "\n\nДля охоты нужна активная лицензия на оружие."
    text = (
        f"{LICENSE_NAMES[license_id]} <b>Лицензия</b>\n\n"
        f"Статус: <b>{'выдана' if owned else 'не выдана'}</b>\n"
        f"Fee в казну: <b>{price:,.2f} RUB</b>{extra}"
    ).replace(",", " ")
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, license_action(license_id, can_pay=not owned))


@router.callback_query(F.data.startswith("licenses:buy:"))
async def buy_license(callback: CallbackQuery, bot: Bot, database: Database, config: Config) -> None:
    await answer_callback(callback)
    license_id = callback.data.split(":")[-1]
    if license_id == "hunting" and not database.has_license(callback.from_user.id, "weapon"):
        await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, "❌ Сначала получите лицензию на оружие.", back_main("licenses:menu"))
        return
    price = config.license_prices.get(license_id, 0.0) if config.license_prices else 0.0
    ok = database.donate_to_treasury(callback.from_user.id, price, f"license_fee:{license_id}")
    if ok:
        database.issue_license(callback.from_user.id, license_id)
        log_action(database, callback.from_user.id, "license_paid", license=license_id, amount=price)
        text = f"✅ Лицензия {LICENSE_NAMES[license_id]} выдана. Fee переведен в казну."
    else:
        text = "❌ Недостаточно средств для оплаты fee."
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("licenses:menu"))


@router.callback_query(F.data.startswith("licenses:exam:"))
async def start_exam(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    await answer_callback(callback)
    license_id = callback.data.split(":")[-1]
    pool, count, need = exam_pool(license_id)
    selected = random.sample(pool, count)
    await state.set_data({"license_id": license_id, "questions": selected, "index": 0, "correct": 0, "need": need})
    await show_question(callback, bot, database, state)


@router.callback_query(F.data.startswith("licenses:answer:"))
async def answer_exam(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    await answer_callback(callback)
    data = await state.get_data()
    index = int(data["index"])
    selected_answer = int(callback.data.split(":")[-1])
    options = data["current_options"]
    current = data["questions"][index]
    if options[selected_answer] == current["a"]:
        data["correct"] += 1
    data["index"] = index + 1
    await state.set_data(data)
    if data["index"] >= len(data["questions"]):
        await finish_exam(callback, bot, database, state, config)
        return
    await show_question(callback, bot, database, state)


async def show_question(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext) -> None:
    data = await state.get_data()
    current = data["questions"][data["index"]]
    options = [current["a"], *current["o"]]
    random.shuffle(options)
    data["current_options"] = options
    await state.set_data(data)
    text = (
        f"📝 <b>Экзамен</b>\n"
        f"Вопрос {data['index'] + 1}/{len(data['questions'])}\n"
        f"Верных: {data['correct']}/{data['need']}\n\n"
        f"{current['q']}"
    )
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, question(options))


async def finish_exam(callback: CallbackQuery, bot: Bot, database: Database, state: FSMContext, config: Config) -> None:
    data = await state.get_data()
    license_id = data["license_id"]
    passed = data["correct"] >= data["need"]
    await state.clear()
    if passed:
        price = config.license_prices.get(license_id, 0.0) if config.license_prices else 0.0
        paid = database.donate_to_treasury(callback.from_user.id, price, f"license_fee:{license_id}")
        if paid:
            database.issue_license(callback.from_user.id, license_id)
            text = (
                f"✅ Экзамен сдан: {data['correct']}/{len(data['questions'])}.\n"
                f"Лицензия {LICENSE_NAMES[license_id]} выдана автоматически, fee ушел в казну."
            )
        else:
            text = (
                f"✅ Экзамен сдан: {data['correct']}/{len(data['questions'])}, "
                "но на балансе не хватило RUB для оплаты fee."
            )
    else:
        text = f"❌ Экзамен не сдан: {data['correct']}/{len(data['questions'])}. Нужно минимум {data['need']}."
    log_action(database, callback.from_user.id, "license_exam", license=license_id, correct=data["correct"], passed=passed)
    await replace_menu(bot, database, callback.message.chat.id, callback.from_user.id, text, back_main("licenses:menu"))
