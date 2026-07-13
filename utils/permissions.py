from __future__ import annotations

from aiogram.types import Message, User

from config import Config
from utils.database import Database


def is_staff_group(message: Message, config: Config) -> bool:
    return config.staff_group_id != 0 and message.chat.id == config.staff_group_id


def is_admin(user: User | None, database: Database) -> bool:
    if not user:
        return False
    admins = database.read("admins").get("ids", [])
    profile = database.get_user(user.id)
    roles = profile.get("roles", []) if profile else []
    return user.id in admins or any("админ" in str(role).lower() or "admin" in str(role).lower() for role in roles)
