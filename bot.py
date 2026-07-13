from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import admin, bank, casino, inventory, licenses, profile, start, treasury
from utils.database import Database


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not config.token:
        raise RuntimeError("Укажите BOT_TOKEN в .env")

    database = Database(config.database_dir, config.legacy_data_path, config.start_balance)
    database.bootstrap()

    bot = Bot(config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage(), database=database, config=config)

    dp.include_router(start.router)
    dp.include_router(bank.router)
    dp.include_router(treasury.router)
    dp.include_router(casino.router)
    dp.include_router(inventory.router)
    dp.include_router(profile.router)
    dp.include_router(licenses.router)
    dp.include_router(admin.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
